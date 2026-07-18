"""Regression tests for the DSE market-hour automatic scanner scheduler."""

import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.services.scanner_scheduler import MarketScannerScheduler
from app.services.scanner_scheduler_state import ScannerSchedulerStateRepository

_DHAKA = ZoneInfo("Asia/Dhaka")


class FakeScannerService:
    def __init__(self) -> None:
        self.calls = 0

    def run(self) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(ok=True, message="Scheduled scan completed.")


def _scheduler(
    tmp_path: Path,
    service: FakeScannerService,
    *,
    holidays: str = "",
) -> MarketScannerScheduler:
    return MarketScannerScheduler(
        settings=Settings(
            scanner_scheduler_enabled=True,
            dse_market_holidays=holidays,
        ),
        scanner_service=service,  # type: ignore[arg-type]
        state_repository=ScannerSchedulerStateRepository(tmp_path / "scheduler-state.json"),
    )


def test_scheduler_runs_each_market_slot_only_once_and_survives_restart(tmp_path: Path) -> None:
    service = FakeScannerService()
    scheduler = _scheduler(tmp_path, service)

    assert asyncio.run(scheduler.tick(datetime(2026, 7, 19, 9, 59, tzinfo=_DHAKA))) is False
    assert asyncio.run(scheduler.tick(datetime(2026, 7, 19, 10, 0, tzinfo=_DHAKA))) is True
    assert asyncio.run(scheduler.tick(datetime(2026, 7, 19, 10, 45, tzinfo=_DHAKA))) is False
    assert service.calls == 1

    restarted_service = FakeScannerService()
    restarted = _scheduler(tmp_path, restarted_service)
    assert asyncio.run(restarted.tick(datetime(2026, 7, 19, 10, 50, tzinfo=_DHAKA))) is False
    assert restarted_service.calls == 0

    assert asyncio.run(restarted.tick(datetime(2026, 7, 19, 11, 0, tzinfo=_DHAKA))) is True
    assert restarted_service.calls == 1

    state = restarted.status(datetime(2026, 7, 19, 11, 5, tzinfo=_DHAKA))
    assert state.last_slot == "2026-07-19T11:00"
    assert state.last_result_ok is True
    assert state.current_slot == "2026-07-19T11:00"


def test_scheduler_skips_weekends_holidays_and_after_market_close(tmp_path: Path) -> None:
    service = FakeScannerService()
    scheduler = _scheduler(tmp_path, service, holidays="2026-07-19")

    assert asyncio.run(scheduler.tick(datetime(2026, 7, 18, 10, 0, tzinfo=_DHAKA))) is False
    assert asyncio.run(scheduler.tick(datetime(2026, 7, 19, 10, 0, tzinfo=_DHAKA))) is False
    assert asyncio.run(scheduler.tick(datetime(2026, 7, 20, 14, 31, tzinfo=_DHAKA))) is False
    assert service.calls == 0


def test_scheduler_uses_locked_hourly_slots_and_next_slot(tmp_path: Path) -> None:
    service = FakeScannerService()
    scheduler = _scheduler(tmp_path, service)

    status = scheduler.status(datetime(2026, 7, 19, 9, 0, tzinfo=_DHAKA))
    assert status.slots == ["10:00", "11:00", "12:00", "13:00", "14:00"]
    assert status.market_window == "10:00-14:30 BDT"
    assert status.next_slot_at == datetime(2026, 7, 19, 10, 0, tzinfo=_DHAKA)

    assert asyncio.run(scheduler.tick(datetime(2026, 7, 19, 14, 30, tzinfo=_DHAKA))) is True
    assert service.calls == 1
