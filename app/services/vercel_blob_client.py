"""Vercel Blob client for durable DSE Pulse file storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vercel.blob import BlobClient, list_objects
from vercel.blob.errors import BlobError, BlobNotFoundError


@dataclass(frozen=True, slots=True)
class VercelBlobStatus:
    configured: bool
    connected: bool
    message: str


class VercelBlobClient:
    """Read and replace private blobs using one read-write token."""

    def __init__(self, token: str = "") -> None:
        self._token = token.strip()
        self._client = BlobClient()

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def status(self) -> VercelBlobStatus:
        if not self.configured:
            return VercelBlobStatus(
                configured=False,
                connected=False,
                message="Vercel Blob storage is not configured.",
            )
        try:
            list_objects(limit=1, token=self._token)
        except BlobError:
            return VercelBlobStatus(
                configured=True,
                connected=False,
                message="Vercel Blob storage is configured but unavailable.",
            )
        return VercelBlobStatus(
            configured=True,
            connected=True,
            message="Vercel Blob storage is connected.",
        )

    def download(self, pathname: str) -> bytes | None:
        if not self.configured:
            return None
        try:
            result = self._client.get(pathname, access="private", token=self._token)
        except BlobNotFoundError:
            return None
        except BlobError as exc:
            raise RuntimeError("Vercel Blob master file could not be downloaded.") from exc
        if result is None or result.status_code != 200 or result.stream is None:
            return None
        stream: Any = result.stream
        if hasattr(stream, "read"):
            data = stream.read()
            return bytes(data)
        return b"".join(stream)

    def upload_or_replace(self, pathname: str, content: bytes, content_type: str) -> str:
        if not self.configured:
            raise RuntimeError("Vercel Blob storage is not configured.")
        try:
            result = self._client.put(
                pathname,
                content,
                access="private",
                content_type=content_type,
                add_random_suffix=False,
                overwrite=True,
                cache_control_max_age=60,
                token=self._token,
            )
        except BlobError as exc:
            raise RuntimeError("Vercel Blob master file could not be saved.") from exc
        return result.pathname
