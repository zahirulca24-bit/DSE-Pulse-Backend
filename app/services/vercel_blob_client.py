"""Vercel Blob client for durable DSE Pulse file storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from vercel.blob import BlobClient, list_objects
    from vercel.blob.errors import BlobError, BlobNotFoundError
except ModuleNotFoundError:  # pragma: no cover - exercised when optional storage SDK is absent
    BlobClient = None  # type: ignore[assignment,misc]
    list_objects = None  # type: ignore[assignment]

    class BlobError(Exception):
        """Fallback error used when the optional Vercel SDK is unavailable."""

    class BlobNotFoundError(BlobError):
        """Fallback not-found error used when the optional Vercel SDK is unavailable."""


@dataclass(frozen=True, slots=True)
class VercelBlobStatus:
    configured: bool
    connected: bool
    message: str


class VercelBlobClient:
    """Read and replace private blobs using one read-write token."""

    def __init__(self, token: str = "") -> None:
        self._token = token.strip()
        self._client: Any | None = None
        if self._token and BlobClient is not None:
            self._client = BlobClient(token=self._token)

    @property
    def configured(self) -> bool:
        return bool(self._token)

    @property
    def sdk_available(self) -> bool:
        return BlobClient is not None and list_objects is not None

    def status(self) -> VercelBlobStatus:
        if not self.configured:
            return VercelBlobStatus(
                configured=False,
                connected=False,
                message="Vercel Blob storage is not configured.",
            )
        if not self.sdk_available:
            return VercelBlobStatus(
                configured=True,
                connected=False,
                message="Vercel Blob storage is configured but its SDK is unavailable.",
            )
        try:
            assert list_objects is not None
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
        if self._client is None:
            raise RuntimeError("Vercel Blob SDK is unavailable.")
        try:
            result = self._client.get(pathname, access="private")
        except BlobNotFoundError:
            return None
        except BlobError as exc:
            raise RuntimeError("Vercel Blob master file could not be downloaded.") from exc
        if result.status_code != 200:
            return None
        return result.content

    def upload_or_replace(self, pathname: str, content: bytes, content_type: str) -> str:
        if not self.configured:
            raise RuntimeError("Vercel Blob storage is not configured.")
        if self._client is None:
            raise RuntimeError("Vercel Blob SDK is unavailable.")
        try:
            result = self._client.put(
                pathname,
                content,
                access="private",
                content_type=content_type,
                add_random_suffix=False,
                overwrite=True,
                cache_control_max_age=60,
            )
        except BlobError as exc:
            raise RuntimeError("Vercel Blob master file could not be saved.") from exc
        return result.pathname
