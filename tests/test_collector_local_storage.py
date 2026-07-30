"""Regression tests for the database-free local collector path."""

from datetime import date
from pathlib import Path

from app.core.config import Settings
from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.schemas.ohlc import OhlcRow
from app.services.collector_job_repository import CollectorJobRepository
from app.services.collector_service import CollectorService
from app.services.collector_source import CollectorBatch
from app.services.ohlc_repository import OhlcRepository


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
) -> tuple[CollectorService, CollectorJobRepository, OhlcRepository, FakeCollectorSource]:
    job_repository = CollectorJobRepository(tmp_path / "collector_jobs.json")
    ohlc_repository = OhlcRepository(tmp_path / "dse_ohlc.csv")
    source = FakeCollectorSource()
    service = CollectorService(
        settings=Settings(collector_admin_token="secret"),
        repository=job_repository,
        ohlc_repository=ohlc_repository,
        source=source,
    )
    return service, job_repository, ohlc_repository, source


def test_collector_merges_daily_rows_into_local_storage(tmp_path: Path) -> None:
    service, _jobs, ohlc, source = _service(tmp_path)

    service.authorize("secret")
    job = service.start(date(2026, 7, 16))
    service.execute(job.job_id, collect_missing=False)

    completed = service.get(job.job_id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.inserted_rows == 1
    assert completed.updated_rows == 0
    assert completed.scanner_refresh_required is True
    assert any("local OHLC storage updated" in item for item in completed.warnings)
    assert [row.symbol for row in ohlc.get_all_rows()] == ["ACI"]
    assert source.allowed_symbols == set(PHASE1_SYMBOLS)


def test_collector_upserts_existing_symbol_date(tmp_path: Path) -> None:
    service, _jobs, ohlc, _source = _service(tmp_path)

    first = service.start(date(2026, 7, 16))
    service.execute(first.job_id, collect_missing=False)
    second = service.start(date(2026, 7, 16))
    service.execute(second.job_id, collect_missing=False)

    completed = service.get(second.job_id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.inserted_rows == 0
    assert completed.updated_rows == 1
    assert len(ohlc.get_all_rows()) == 1


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
