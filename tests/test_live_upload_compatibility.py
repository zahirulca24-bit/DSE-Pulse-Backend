"""Regression coverage for the currently deployed frontend upload contract."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.blob_ohlc_repository import BlobOhlcRepository
from app.services.dependencies import get_blob_ohlc_repository
from app.services.ohlc_repository import OhlcRepository
from app.services.vercel_blob_client import VercelBlobStatus


class FakeBlobClient:
    def __init__(self) -> None:
        self.content: bytes | None = None
        self.saved_pathname: str | None = None

    @property
    def configured(self) -> bool:
        return True

    def status(self) -> VercelBlobStatus:
        return VercelBlobStatus(
            configured=True,
            connected=True,
            message="Vercel Blob storage is connected.",
        )

    def download(self, pathname: str) -> bytes | None:
        return self.content

    def upload_or_replace(self, pathname: str, content: bytes, content_type: str) -> str:
        assert content_type == "text/csv"
        self.saved_pathname = pathname
        self.content = content
        return pathname


def test_live_frontend_drive_routes_save_to_blob(
    client: TestClient,
    isolated_storage: Path,
) -> None:
    fake = FakeBlobClient()
    repository = BlobOhlcRepository(
        local_repository=OhlcRepository(isolated_storage),
        blob_client=fake,  # type: ignore[arg-type]
        master_pathname="dse/DSE_OHLC_MASTER.csv",
    )

    def override_blob_repository() -> BlobOhlcRepository:
        return repository

    app.dependency_overrides[get_blob_ohlc_repository] = override_blob_repository
    payload = (
        b"symbol,trade_date,open,high,low,close,volume\n"
        b"ACI,2026-07-20,280,286,278,284,510000\n"
    )

    try:
        status_response = client.get("/drive/status")
        import_response = client.post(
            "/data/ohlc/import-drive",
            files={"file": ("ohlc.csv", payload, "text/csv")},
        )
    finally:
        app.dependency_overrides.pop(get_blob_ohlc_repository, None)

    assert status_response.status_code == 200
    assert status_response.json() == {
        "configured": True,
        "connected": True,
        "storage_type": "google_drive",
        "folder_name": "Vercel Blob",
        "master_filename": "DSE_OHLC_MASTER.csv",
        "message": "Vercel Blob storage is connected.",
    }
    assert import_response.status_code == 200
    assert import_response.json()["ok"] is True
    assert import_response.json()["data_source"] == "google_drive"
    assert import_response.json()["inserted_rows"] == 1
    assert import_response.json()["rows_count"] == 1
    assert import_response.json()["master_filename"] == "DSE_OHLC_MASTER.csv"
    assert fake.saved_pathname == "dse/DSE_OHLC_MASTER.csv"
