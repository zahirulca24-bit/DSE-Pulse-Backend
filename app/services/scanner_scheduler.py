"""Bangladesh market-hour scheduler for automatic scanner execution."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.schemas.scanner_scheduler import ScannerSchedulerStatusResponse
from app.services.scanner_scheduler_state import ScannerSchedulerStateRepository
from app.services.scanner_service import ScannerService

_DHAKA = ZoneInfo("Asia/Dhaka")
_MARKET_OPEN = time(10, 0)
_MARKET_CLOSE = time(14, 30)
_SCAN_TIMES = (time(10, 0), time(11, 0), time(12, 0), time(13, 0), time(14, 0))
_POLL_SECONDS = 30


class MarketScannerScheduler:
    """Run at most one scan for each approved market-hour slot."""

    def __init__(
        self,
        *,
        settings: Settings,
        scanner_service: ScannerService,
        state_repository: ScannerSchedulerStateRepository,
    ) -> None:
        self._settings = settings
        self._scanner_service = scanner_service
        self._state_repository = state_repository
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    @property
    def enabled(self) -> bool:
        return self._settings.scanner_scheduler_enabled

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop(), name="dse-market-scanner-scheduler")

    async def stop(self) -> None:
        self._stopping = True
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def tick(self, now: datetime | None = None) -> bool:
        """Execute the most recent due slot once; return whether a scan was attempted."""

        current = self._normalize_now(now)
        slot = self._due_slot(current)
        if slot is None:
            return False
        slot_id = slot.strftime("%Y-%m-%dT%H:%M")
        if not self._state_repository.claim(slot_id):
            return False

        try:
            result = await asyncio.to_thread(self._scanner_service.run)
            self._state_repository.complete(ok=result.ok, message=result.message)
        except Exception as exc:  # scheduler must stay alive after one failed scan
            self._state_repository.complete(
                ok=False,
                message=f"Scheduled scanner failed safely: {type(exc).__name__}.",
            )
        return True

    def status(self, now: datetime | None = None) -> ScannerSchedulerStatusResponse:
        current = self._normalize_now(now)
        state = self._state_repository.load()
        due = self._due_slot(current)
        return ScannerSchedulerStatusResponse(
            enabled=self.enabled,
            running=self.running,
            timezone="Asia/Dhaka",
            market_window="10:00-14:30 BDT",
            slots=[item.strftime("%H:%M") for item in _SCAN_TIMES],
            current_slot=None if due is None else due.strftime("%Y-%m-%dT%H:%M"),
            next_slot_at=self._next_slot(current),
            last_slot=state.last_slot,
            last_started_at=state.last_started_at,
            last_completed_at=state.last_completed_at,
            last_result_ok=state.last_result_ok,
            last_message=state.last_message,
        )

    async def _loop(self) -> None:
        while not self._stopping:
            await self.tick()
            await asyncio.sleep(_POLL_SECONDS)

    def _due_slot(self, now: datetime) -> datetime | None:
        if not self._is_market_day(now.date()):
            return None
        local_time = now.timetz().replace(tzinfo=None)
        if local_time < _MARKET_OPEN or local_time > _MARKET_CLOSE:
            return None
        due_times = [slot for slot in _SCAN_TIMES if slot <= local_time]
        if not due_times:
            return None
        return datetime.combine(now.date(), due_times[-1], tzinfo=_DHAKA)

    def _next_slot(self, now: datetime) -> datetime | None:
        candidate_date = now.date()
        for day_offset in range(0, 15):
            day = candidate_date + timedelta(days=day_offset)
            if not self._is_market_day(day):
                continue
            for slot in _SCAN_TIMES:
                candidate = datetime.combine(day, slot, tzinfo=_DHAKA)
                if candidate > now:
                    return candidate
        return None

    def _is_market_day(self, day: date) -> bool:
        if day.weekday() in (4, 5):  # Friday and Saturday
            return False
        return day not in self._settings.dse_market_holiday_dates

    @staticmethod
    def _normalize_now(now: datetime | None) -> datetime:
        if now is None:
            return datetime.now(_DHAKA)
        if now.tzinfo is None:
            return now.replace(tzinfo=_DHAKA)
        return now.astimezone(_DHAKA)
