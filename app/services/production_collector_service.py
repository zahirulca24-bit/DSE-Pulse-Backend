"""Production collector orchestration backed by SQL storage."""

from __future__ import annotations

from datetime import date

from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.repositories.collector_repository import CollectorDbRepository
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.collector import CollectorStatusResponse
from app.services.collector_source import CollectorSource, CollectorSourceError


class ProductionCollectorUnavailableError(RuntimeError):
    """Raised when no verified production collector is configured."""


class ProductionCollectorDatabaseError(RuntimeError):
    """Raised when collector state or OHLC tables are unavailable."""


class ProductionCollectorService:
    """Run verified collector adapters without demo-data fallback."""

    def __init__(
        self,
        *,
        repository: CollectorDbRepository,
        ohlc_repository: OhlcDbRepository,
        source: CollectorSource | None,
        source_name: str | None,
    ) -> None:
        self._repository = repository
        self._ohlc_repository = ohlc_repository
        self._source = source
        self._source_name = source_name

    def status(self) -> CollectorStatusResponse:
        return self._repository.get_status(self._source_name)

    def start(self) -> CollectorStatusResponse:
        self._ensure_database()
        return self._repository.set_enabled(True, self._source_name)

    def stop(self) -> CollectorStatusResponse:
        self._ensure_database()
        return self._repository.set_enabled(False, self._source_name)

    def run(self, trade_date: date | None = None) -> CollectorStatusResponse:
        self._ensure_database()
        source = self._source
        if source is None:
            message = (
                "Automated DSE collection is unavailable because no verified "
                "production source adapter is configured. Import a validated CSV "
                "with POST /data/import."
            )
            self._repository.mark_failed(self._source_name, message)
            raise ProductionCollectorUnavailableError(message)

        target_date = trade_date or date.today()
        self._repository.mark_started(source.name)
        try:
            batch = source.collect_range(target_date, target_date, set(PHASE1_SYMBOLS))
            inserted, updated = self._ohlc_repository.upsert(batch.rows)
            if inserted + updated == 0 and batch.rows:
                raise ProductionCollectorDatabaseError(
                    "Collector rows could not be persisted to database."
                )
            self._repository.mark_completed(
                source=source.name,
                symbols_updated=len({row.symbol for row in batch.rows}),
                inserted_rows=inserted,
                updated_rows=updated,
                rejected_rows=batch.invalid_rows,
            )
            return self.status()
        except CollectorSourceError as exc:
            self._repository.mark_failed(source.name, str(exc))
            raise ProductionCollectorUnavailableError(str(exc)) from exc

    def _ensure_database(self) -> None:
        if not self._repository.is_available() or not self._ohlc_repository.is_available():
            raise ProductionCollectorDatabaseError(
                "Database tables are unavailable. Run POST /db/init first."
            )
