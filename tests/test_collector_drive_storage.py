"""Regression tests for the database-free Google Drive collector path."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.schemas.ohlc import OhlcRow
from app.services.collector_job_repository import CollectorJobRepository
from app.services.collector_service import CollectorService, CollectorUnavailableError
from app.services.collector_source import CollectorBatch
from app.services.csv_ingestion_service import CsvParseResult
from app.services.google_drive_client import GoogleDriveStatus


class FakeDriveRepository:
    def __init__(self, connected: bool = True) -> None:
        self.connected = connected
        self.synced = False
        self.merged_rows: list[OhlcRow] = []

    def drive_status(self) -> GoogleDriveStatus:
        return GoogleDriveStatus(
            configured=self.connected,
            connected=self.connected,
            message="Drive ready." if self.connected else "Drive unavailable.",
        )

    def sync_from_drive(self, force: bool = False) -> bool:
        self.synced = force
        return self.connected

    def get_status(self) -> SimpleNamespace:
        return SimpleNamespace(latest_trade_date=date(2026, 7, 15))

    def merge_and_save_to_drive(
        self,
        parsed: CsvParseResult,
    ) -> tuple[int, int, CsvParseResult]:
        self.merged_rows = list(parsed.valid_rows)
        return len(parsed.valid_rows), 0, parsed


class FakeCollectorSource:
    name = "fake-dse-source"

    def __init__(self) -> None:
        self.allowed_symbols: set[str] = set()

    def collect_range(
        self,
        start_date: date,
        end_date: date,
        allowed_symbols: set[str],
    ) -> CollectorBatch:
        self.allowed_symbols = set(allowed_symbols)
        row = OhlcRow(
            symbol="ACI",
            trade_date=end_date,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=100_000,
            trade=None,
            value=None,
        )
        return CollectorBatch(
            rows=[row],
            fetched_rows=1,
            invalid_rows=0,
            missing_symbols=[],
            warnings=[],
        )


def _service(
    tmp_path: Path,
    drive: FakeDriveRepository,
) -> tuple[CollectorService, CollectorJobRepository, FakeCollectorSource]:
    repository = CollectorJobRepository(tmp_path / "collector_jobs.json")
    source = FakeCollectorSource()
    service = CollectorService(
        settings=Settings(collector_admin_token="secret"),
        repository=repository,
        ohlc_repository=drive,  # type: ignore[arg-type]
        source=source,
    )
    return service, repository, source


def test_collector_merges_daily_rows_into_drive_without_database(tmp_path: Path) -> None:
    drive = FakeDriveRepository()
    service, _repository, source = _service(tmp_path, drive)

    service.authorize("secret")
    job = service.start(date(2026, 7, 16))
    service.execute(job.job_id, collect_missing=False)

    completed = service.get(job.job_id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.inserted_rows == 1
    assert completed.updated_rows == 0
    assert completed.scanner_refresh_required is True
    assert any("Google Drive master updated" in item for item in completed.warnings)
    assert drive.synced is True
    assert [row.symbol for row in drive.merged_rows] == ["ACI"]
    assert source.allowed_symbols == set(PHASE1_SYMBOLS)


def test_collector_fails_closed_when_drive_is_unavailable(tmp_path: Path) -> None:
    service, _repository, _source = _service(tmp_path, FakeDriveRepository(connected=False))

    with pytest.raises(CollectorUnavailableError, match="Google Drive OHLC storage is unavailable"):
        service.start(date(2026, 7, 16))


def test_collector_job_state_persists_without_database(tmp_path: Path) -> None:
    path = tmp_path / "collector_jobs.json"
    repository = CollectorJobRepository(path)
    job = repository.create(date(2026, 7, 16), "test-source")
    assert repository.mark_running(job.job_id) is True
    assert repository.mark_completed(
        job.job_id,
        fetched_rows=10,
        collected_symbols=2,
        inserted_rows=8,
        updated_rows=2,
        invalid_rows=0,
        missing_symbols=[],
        warnings=["done"],
    ) is True

    reloaded = CollectorJobRepository(path).get(job.job_id)
    assert reloaded is not None
    assert reloaded.status == "completed"
    assert reloaded.inserted_rows == 8
    assert reloaded.updated_rows == 2
