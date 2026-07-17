"""Manual DSE collection orchestration and database upsert workflow."""

from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.repositories.collector_repository import CollectorRepository
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.collector import CollectorRunResponse
from app.schemas.ohlc import OhlcRow
from app.services.collector_source import CollectorSource, CollectorSourceError
from app.services.data_audit_service import DataAuditService

_MAX_BACKFILL_CALENDAR_DAYS = 45


class CollectorDisabledError(RuntimeError):
    """Raised when a collector admin token is not configured."""


class CollectorAuthorizationError(RuntimeError):
    """Raised when the supplied collector token is invalid."""


class CollectorConflictError(RuntimeError):
    """Raised when another collection job is already active."""


class CollectorUnavailableError(RuntimeError):
    """Raised when collector database tables or OHLC storage are unavailable."""


class CollectorService:
    """Create, execute, and inspect safe manual collector jobs."""

    def __init__(
        self,
        *,
        settings: Settings,
        repository: CollectorRepository,
        ohlc_repository: OhlcDbRepository,
        audit_service: DataAuditService,
        source: CollectorSource,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._ohlc_repository = ohlc_repository
        self._audit_service = audit_service
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
        if not self._repository.is_available():
            raise CollectorUnavailableError("Collector table is unavailable. Run POST /db/init after deployment.")
        if not self._ohlc_repository.is_available():
            raise CollectorUnavailableError("Database OHLC storage is unavailable.")
        self._repository.fail_stale_active()
        active = self._repository.get_active()
        if active is not None:
            raise CollectorConflictError(f"Collector job {active.job_id} is already {active.status}.")

        trade_date = requested_trade_date or self._default_trade_date()
        if trade_date > datetime.now(ZoneInfo("Asia/Dhaka")).date():
            raise ValueError("Future trade dates are not allowed.")
        job = self._repository.create(trade_date, self._source.name)
        if job is None:
            raise CollectorUnavailableError("Collector job could not be created safely.")
        return job

    def execute(self, job_id: str, collect_missing: bool = True) -> None:
        job = self._repository.get(job_id)
        if job is None:
            return
        if not self._repository.mark_running(job_id):
            return

        try:
            symbols_response = self._ohlc_repository.get_symbols()
            allowed_symbols = set(symbols_response.symbols)
            if not allowed_symbols:
                raise CollectorUnavailableError("Approved OHLC universe is empty.")

            collection_dates = self._collection_dates(job.requested_trade_date, collect_missing)
            all_rows: list[OhlcRow] = []
            fetched_rows = 0
            invalid_rows = 0
            latest_missing_symbols: list[str] = []
            warnings: list[str] = []
            successful_dates: list[date] = []

            for collection_date in collection_dates:
                try:
                    batch = self._source.collect(collection_date, allowed_symbols)
                except CollectorSourceError as exc:
                    warnings.append(f"{collection_date.isoformat()}: {exc}")
                    continue
                all_rows.extend(batch.rows)
                fetched_rows += batch.fetched_rows
                invalid_rows += batch.invalid_rows
                latest_missing_symbols = batch.missing_symbols
                warnings.extend(f"{collection_date.isoformat()}: {warning}" for warning in batch.warnings)
                successful_dates.append(collection_date)

            if not all_rows:
                raise CollectorSourceError("No requested trading date produced valid DSE rows.")

            inserted, updated = self._ohlc_repository.upsert(all_rows)
            if inserted + updated == 0:
                raise CollectorUnavailableError("Collector rows could not be upserted into database storage.")

            warnings.insert(
                0,
                f"Collected {len(successful_dates)} of {len(collection_dates)} trading-day candidates.",
            )
            audit = self._audit_service.audit()
            if not audit.scanner_ready:
                warnings.append("Post-collection OHLC audit is not scanner-ready; review /data/audit.")
            self._repository.mark_completed(
                job_id,
                fetched_rows=fetched_rows,
                collected_symbols=len({row.symbol for row in all_rows}),
                inserted_rows=inserted,
                updated_rows=updated,
                invalid_rows=invalid_rows,
                missing_symbols=latest_missing_symbols,
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
