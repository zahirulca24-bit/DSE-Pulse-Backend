"""Manual DSE collection orchestration using Google Drive as canonical OHLC storage."""

from __future__ import annotations

import secrets
from collections import Counter
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.schemas.collector import CollectorRunResponse
from app.services.collector_job_repository import CollectorJobRepository
from app.services.collector_source import CollectorSource, CollectorSourceError
from app.services.csv_ingestion_service import NORMALIZED_HEADERS, CsvParseResult
from app.services.drive_ohlc_repository import DriveOhlcRepository

_MAX_BACKFILL_CALENDAR_DAYS = 45
_MINIMUM_SCANNER_ROWS = 60


class CollectorDisabledError(RuntimeError):
    """Raised when a collector admin token is not configured."""


class CollectorAuthorizationError(RuntimeError):
    """Raised when the supplied collector token is invalid."""


class CollectorConflictError(RuntimeError):
    """Raised when another collection job is already active."""


class CollectorUnavailableError(RuntimeError):
    """Raised when Drive-backed collection cannot run safely."""


class CollectorService:
    """Create, execute, and inspect safe manual Drive-backed collector jobs."""

    def __init__(
        self,
        *,
        settings: Settings,
        repository: CollectorJobRepository,
        ohlc_repository: DriveOhlcRepository,
        source: CollectorSource,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._ohlc_repository = ohlc_repository
        self._source = source

    def authorize(self, supplied_token: str | None) -> None:
        configured = self._settings.collector_admin_token.strip()
        if not configured:
            raise CollectorDisabledError(
                "Collector is disabled until COLLECTOR_ADMIN_TOKEN is configured on the backend."
            )
        supplied = (supplied_token or "").strip()
        if not supplied or not secrets.compare_digest(configured, supplied):
            raise CollectorAuthorizationError("Collector authorization failed.")

    def start(self, requested_trade_date: date | None) -> CollectorRunResponse:
        drive_status = self._ohlc_repository.drive_status()
        if not drive_status.connected:
            raise CollectorUnavailableError(
                "Google Drive OHLC storage is unavailable. " + drive_status.message
            )
        self._repository.fail_stale_active()
        active = self._repository.get_active()
        if active is not None:
            raise CollectorConflictError(
                f"Collector job {active.job_id} is already {active.status}."
            )

        trade_date = requested_trade_date or self._default_trade_date()
        if trade_date > datetime.now(ZoneInfo("Asia/Dhaka")).date():
            raise ValueError("Future trade dates are not allowed.")
        return self._repository.create(trade_date, self._source.name)

    def execute(self, job_id: str, collect_missing: bool = True) -> None:
        job = self._repository.get(job_id)
        if job is None:
            return
        if not self._repository.mark_running(job_id):
            return

        try:
            drive_status = self._ohlc_repository.drive_status()
            if not drive_status.connected:
                raise CollectorUnavailableError(
                    "Google Drive OHLC storage is unavailable. " + drive_status.message
                )

            self._ohlc_repository.sync_from_drive(force=True)
            allowed_symbols = set(PHASE1_SYMBOLS)
            collection_dates = self._collection_dates(
                job.requested_trade_date,
                collect_missing,
            )
            requested_dates = set(collection_dates)
            batch = self._source.collect_range(
                collection_dates[0],
                collection_dates[-1],
                allowed_symbols,
            )
            all_rows = [row for row in batch.rows if row.trade_date in requested_dates]
            if not all_rows:
                raise CollectorSourceError(
                    "No requested trading date produced valid DSE rows."
                )

            parsed = CsvParseResult(
                filename=f"collector-{job.requested_trade_date.isoformat()}.csv",
                detected_headers=list(NORMALIZED_HEADERS),
                valid_rows=all_rows,
                invalid_rows=batch.invalid_rows,
                warnings=list(batch.warnings),
                errors=[],
            )
            inserted, updated, merged = self._ohlc_repository.merge_and_save_to_drive(parsed)
            if inserted + updated == 0:
                raise CollectorUnavailableError(
                    "Collector rows could not be merged into the Google Drive OHLC master."
                )

            successful_dates = sorted({row.trade_date for row in all_rows})
            warnings = list(batch.warnings)
            warnings.insert(
                0,
                f"Collected {len(successful_dates)} of "
                f"{len(collection_dates)} trading-day candidates.",
            )
            warnings.append(
                "Google Drive master updated and the backend local OHLC cache refreshed."
            )

            approved_counts = Counter(
                row.symbol for row in merged.valid_rows if row.symbol in PHASE1_SYMBOLS
            )
            eligible_symbols = sum(
                count >= _MINIMUM_SCANNER_ROWS for count in approved_counts.values()
            )
            if eligible_symbols == 0:
                warnings.append(
                    "Post-collection cache has no Phase-1 symbol with the minimum 60 rows required by the scanner."
                )

            self._repository.mark_completed(
                job_id,
                fetched_rows=batch.fetched_rows,
                collected_symbols=len({row.symbol for row in all_rows}),
                inserted_rows=inserted,
                updated_rows=updated,
                invalid_rows=batch.invalid_rows,
                missing_symbols=batch.missing_symbols,
                warnings=warnings,
            )
        except CollectorSourceError as exc:
            self._repository.mark_failed(job_id, str(exc))
        except (CollectorUnavailableError, RuntimeError, ValueError) as exc:
            self._repository.mark_failed(job_id, str(exc))

    def get(self, job_id: str) -> CollectorRunResponse | None:
        return self._repository.get(job_id)

    def latest(self) -> CollectorRunResponse | None:
        return self._repository.latest()

    def history(self, limit: int) -> list[CollectorRunResponse]:
        return self._repository.history(limit)

    def _collection_dates(self, target_date: date, collect_missing: bool) -> list[date]:
        if not collect_missing:
            return [target_date]
        status = self._ohlc_repository.get_status()
        latest = status.latest_trade_date
        if latest is None or latest >= target_date:
            return [target_date]
        if (target_date - latest).days > _MAX_BACKFILL_CALENDAR_DAYS:
            raise ValueError(
                f"Automatic backfill is limited to {_MAX_BACKFILL_CALENDAR_DAYS} calendar days; "
                "run a specific trade date instead."
            )

        dates: list[date] = []
        candidate = latest + timedelta(days=1)
        while candidate <= target_date:
            if candidate.weekday() not in (4, 5):
                dates.append(candidate)
            candidate += timedelta(days=1)
        return dates or [target_date]

    @staticmethod
    def _default_trade_date() -> date:
        """Choose the latest completed Bangladesh trading-day candidate."""

        now = datetime.now(ZoneInfo("Asia/Dhaka"))
        candidate = now.date()
        if now.time() < time(15, 0):
            candidate -= timedelta(days=1)
        while candidate.weekday() in (4, 5):
            candidate -= timedelta(days=1)
        return candidate
