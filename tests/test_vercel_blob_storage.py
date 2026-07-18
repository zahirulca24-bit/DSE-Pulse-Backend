"""Vercel Blob master-storage behavior without external credentials."""

from pathlib import Path

from app.services.blob_ohlc_repository import BlobOhlcRepository
from app.services.csv_ingestion_service import CsvIngestionService
from app.services.ohlc_repository import OhlcRepository
from app.services.vercel_blob_client import VercelBlobStatus


class FakeBlobClient:
    def __init__(self, initial: bytes | None = None) -> None:
        self.content = initial
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


def _csv(*rows: str) -> bytes:
    header = "symbol,trade_date,open,high,low,close,volume\n"
    return (header + "\n".join(rows) + "\n").encode()


def _repository(tmp_path: Path, fake: FakeBlobClient) -> BlobOhlcRepository:
    local = OhlcRepository(tmp_path / "storage" / "dse_ohlc.csv")
    return BlobOhlcRepository(
        local_repository=local,
        blob_client=fake,  # type: ignore[arg-type]
        master_pathname="dse/DSE_OHLC_MASTER.csv",
    )


def test_blob_merge_upserts_symbol_date_and_refreshes_cache(tmp_path: Path) -> None:
    fake = FakeBlobClient(
        _csv(
            "ACI,2026-07-15,280,286,278,284,510000",
            "BATBC,2026-07-15,420,425,418,423,100000",
        )
    )
    repository = _repository(tmp_path, fake)
    uploaded = CsvIngestionService().parse_bytes(
        _csv(
            "ACI,2026-07-15,281,287,279,285,520000",
            "SQURPHARMA,2026-07-16,210,215,208,212,200000",
        ),
        "update.csv",
    )

    inserted, updated, merged = repository.merge_and_save_to_blob(uploaded)

    assert inserted == 1
    assert updated == 1
    assert len(merged.valid_rows) == 3
    assert merged.symbols_count == 3
    assert merged.latest_trade_date.isoformat() == "2026-07-16"
    assert fake.saved_pathname == "dse/DSE_OHLC_MASTER.csv"
    assert repository.get_status().rows_count == 3


def test_fresh_repository_restores_master_from_blob(tmp_path: Path) -> None:
    fake = FakeBlobClient(
        _csv(
            "ACI,2026-07-15,280,286,278,284,510000",
            "ACI,2026-07-16,284,288,283,287,450000",
        )
    )
    repository = _repository(tmp_path, fake)

    status = repository.get_status()

    assert status.data_available is True
    assert status.rows_count == 2
    assert status.symbols_count == 1
    assert status.latest_trade_date.isoformat() == "2026-07-16"
    assert repository.storage_path.is_file()
