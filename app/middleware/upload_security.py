"""Fail-closed protection for bulk OHLC upload endpoints."""

from __future__ import annotations

import json
import secrets
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

from app.core.config import Settings

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
SettingsProvider = Callable[[], Settings]

_PROTECTED_UPLOAD_PATHS = frozenset(
    {
        "/data/ohlc/import",
        "/data/ohlc/import-blob",
        "/data/ohlc/import-drive",
        "/data/ohlc/import-db",
    }
)


class UploadSecurityMiddleware:
    """Authenticate and size-limit canonical data mutation requests."""

    def __init__(self, app: ASGIApp, settings_provider: SettingsProvider) -> None:
        self._app = app
        self._settings_provider = settings_provider

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        if method != "POST" or path not in _PROTECTED_UPLOAD_PATHS:
            await self._app(scope, receive, send)
            return

        settings = self._settings_provider()
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        configured = settings.data_admin_token.strip()
        supplied = headers.get("x-data-admin-token", "").strip()

        if not configured:
            await self._json_error(
                send,
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Data imports are disabled until DATA_ADMIN_TOKEN is configured.",
            )
            return
        if not supplied or not secrets.compare_digest(configured, supplied):
            await self._json_error(send, HTTPStatus.FORBIDDEN, "Data import authorization failed.")
            return

        limit = max(settings.max_upload_bytes, 1)
        content_length = headers.get("content-length", "").strip()
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._json_error(send, HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.")
                return
            if declared_size < 0:
                await self._json_error(send, HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.")
                return
            if declared_size > limit:
                await self._payload_too_large(send, limit)
                return

        buffered: list[Message] = []
        received = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                buffered.append(message)
                break
            received += len(message.get("body", b""))
            if received > limit:
                await self._payload_too_large(send, limit)
                return
            buffered.append(message)
            if not message.get("more_body", False):
                break

        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self._app(scope, replay, send)

    @classmethod
    async def _payload_too_large(cls, send: Send, limit: int) -> None:
        limit_mb = limit / (1024 * 1024)
        await cls._json_error(
            send,
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"Upload exceeds the configured {limit_mb:g} MB limit.",
        )

    @staticmethod
    async def _json_error(send: Send, status_code: HTTPStatus, detail: str) -> None:
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": int(status_code),
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
