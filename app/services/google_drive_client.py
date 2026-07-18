"""Small Google Drive client for durable DSE Pulse file storage."""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


@dataclass(frozen=True, slots=True)
class GoogleDriveStatus:
    configured: bool
    connected: bool
    message: str
    folder_name: str | None = None


class GoogleDriveClient:
    """Read and replace files inside one configured Google Drive folder."""

    def __init__(
        self,
        folder_id: str,
        service_account_json: str = "",
        service_account_json_b64: str = "",
    ) -> None:
        self._folder_id = folder_id.strip()
        self._service_account_json = service_account_json.strip()
        self._service_account_json_b64 = service_account_json_b64.strip()
        self._service: Any | None = None

    @property
    def configured(self) -> bool:
        return bool(
            self._folder_id
            and (self._service_account_json or self._service_account_json_b64)
        )

    def status(self) -> GoogleDriveStatus:
        if not self.configured:
            return GoogleDriveStatus(
                configured=False,
                connected=False,
                message="Google Drive storage is not configured.",
            )
        try:
            metadata = (
                self._get_service()
                .files()
                .get(
                    fileId=self._folder_id,
                    fields="id,name,mimeType",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except (HttpError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return GoogleDriveStatus(
                configured=True,
                connected=False,
                message="Google Drive storage is configured but unavailable.",
            )
        if metadata.get("mimeType") != "application/vnd.google-apps.folder":
            return GoogleDriveStatus(
                configured=True,
                connected=False,
                message="Configured Google Drive destination is not a folder.",
            )
        return GoogleDriveStatus(
            configured=True,
            connected=True,
            message="Google Drive storage is connected.",
            folder_name=str(metadata.get("name") or "Google Drive folder"),
        )

    def download_by_name(self, filename: str) -> bytes | None:
        try:
            file_id = self._find_file_id(filename)
            if file_id is None:
                return None
            request = self._get_service().files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except HttpError as exc:
            raise RuntimeError("Google Drive master file could not be downloaded.") from exc

    def upload_or_replace(self, filename: str, content: bytes, mime_type: str) -> str:
        if not self.configured:
            raise RuntimeError("Google Drive storage is not configured.")
        try:
            service = self._get_service()
            media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
            existing_id = self._find_file_id(filename)
            if existing_id:
                result = (
                    service.files()
                    .update(
                        fileId=existing_id,
                        media_body=media,
                        fields="id",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                return str(result["id"])
            result = (
                service.files()
                .create(
                    body={"name": filename, "parents": [self._folder_id]},
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            return str(result["id"])
        except (HttpError, KeyError) as exc:
            raise RuntimeError("Google Drive master file could not be saved.") from exc

    def _find_file_id(self, filename: str) -> str | None:
        escaped = filename.replace("'", "\\'")
        query = (
            f"'{self._folder_id}' in parents and name = '{escaped}' and trashed = false"
        )
        result = (
            self._get_service()
            .files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id,name)",
                pageSize=10,
            )
            .execute()
        )
        files = result.get("files", [])
        return None if not files else str(files[0]["id"])

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        info = self._credential_info()
        credentials = Credentials.from_service_account_info(info, scopes=[_DRIVE_SCOPE])
        self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return self._service

    def _credential_info(self) -> dict[str, Any]:
        if self._service_account_json:
            payload = self._service_account_json
        elif self._service_account_json_b64:
            try:
                payload = base64.b64decode(self._service_account_json_b64).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Invalid base64 Google service-account JSON.") from exc
        else:
            raise ValueError("Google service-account credentials are missing.")
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError("Google service-account JSON must be an object.")
        return parsed
