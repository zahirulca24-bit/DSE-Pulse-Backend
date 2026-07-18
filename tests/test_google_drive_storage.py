"""Google Drive master-storage behavior without external credentials."""

from __future__ import annotations

from pathlib import Path

from app.services.csv_ingestion_service import CsvIngestionService
from app.services.drive_ohlc_repository import DriveOhlcRepository
from app.services.google_drive_client import GoogleDriveStatus
from app.services.ohlc_repository import OhlcRepository


class FakeDriveClient:
    def __init__(self, initial: bytes | None = None) -> None:
        self.content = initial
        self.saved_filename: str | None = None

    @property
    def configured(self) -> bool:
        return True

    def status(self) -> GoogleDriveStatus:
        return GoogleDriveStatus(
            configured=True,
            connected=True,
            message="Google Drive storage is connected.",
            folder_name="Market Data & Backtest Storage",
        )

    def download_by_name(self, filename: str) -> bytes | None:
        return self.content

    def upload_or_replace(self, filename: str, content: bytes, mime_type: str) -> str:
        assert mime_type == "text/csv"
        self.saved_filename = filename
        self.content = content
        return "fake-file-id"


def _csv(*rows: str) -> bytes:
    header = "symbol,trade_date,open,high,low,close,volume\n"
    return (header + "\n".join(rows) + "\n").encode()


def _repository(tmp_path: Path, fake: FakeDriveClient) -> DriveOhlcRepository:
    local = OhlcRepository(tmp_path / "storage" / "dse_ohlc.csv")
    return DriveOhlcRepository(
        local_repository=local,
        drive_client=fake,  # type: ignore[arg-type]
        master_filename="DSE_OHLC_MASTER.csv",
    )


def test_drive_merge_upserts_symbol_date_and_refreshes_cache(tmp_path: Path) -> None:
    fake = FakeDriveClient(
        _csv(
            "GP,2026-07-15,280,286,278,284,510000",
            "BATBC,2026-07-15,420,425,418,423,100000",
        )
    )
    repository = _repository(tmp_path, fake)
    uploaded = CsvIngestionService().parse_bytes(
        _csv(
            "GP,2026-07-15,281,287,279,285,520000",
            "SQURPHARMA,2026-07-16,210,215,208,212,200000",
        ),
        "update.csv",
    )

    inserted, updated, merged = repository.merge_and_save_to_drive(uploaded)

    assert inserted == 1
    assert updated == 1
    assert len(merged.valid_rows) == 3
    assert merged.symbols_count == 3
    assert merged.latest_trade_date.isoformat() == "2026-07-16"
    assert fake.saved_filename == "DSE_OHLC_MASTER.csv"

    gp = repository.get_ohlc("GP", 10, None, None)
    assert gp.rows_count == 1
    assert gp.rows[0].close == 285.0
    assert repository.get_status().rows_count == 3


def test_fresh_repository_restores_master_from_drive(tmp_path: Path) -> None:
    fake = FakeDriveClient(
        _csv(
            "GP,2026-07-15,280,286,278,284,510000",
            "GP,2026-07-16,284,288,283,287,450000",
        )
    )
    repository = _repository(tmp_path, fake)

    status = repository.get_status()

    assert status.data_available is True
    assert status.rows_count == 2
    assert status.symbols_count == 1
    assert status.latest_trade_date.isoformat() == "2026-07-16"
    assert repository.storage_path.is_file()


def test_drive_status_does_not_need_real_google_credentials(tmp_path: Path) -> None:
    fake = FakeDriveClient()
    repository = _repository(tmp_path, fake)

    status = repository.drive_status()

    assert status.configured is True
    assert status.connected is True
    assert status.folder_name == "Market Data & Backtest Storage"
