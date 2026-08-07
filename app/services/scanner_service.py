"""Scanner readiness, source selection, execution, and persistence service."""

from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.scanner import ScannerStatusResponse
from app.schemas.scanner_result import ScannerResultResponse
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository


class ScannerService:
    """Single scanner path shared by manual, scheduled, and read endpoints.

    Database OHLC and scanner persistence are authoritative whenever verified
    database rows exist. Production never falls back to ephemeral local disk.
    Local CSV/JSON remains available only as a non-production development path.
    """

    def __init__(
        self,
        ohlc_cache: OhlcRepository,
        scanner_repository: ScannerRepository,
        scanner_engine: ScannerEngine | None = None,
        *,
        database_ohlc_repository: OhlcDbRepository | None = None,
        database_scanner_repository: ScannerDbRepository | None = None,
        production: bool = False,
    ) -> None:
        self._ohlc_cache = ohlc_cache
        self._scanner_repository = scanner_repository
        self._scanner_engine = scanner_engine
        self._database_ohlc_repository = database_ohlc_repository
        self._database_scanner_repository = database_scanner_repository
        self._production = production

    def get_status(self) -> ScannerStatusResponse:
        database_data_available = self._database_data_available()
        if database_data_available:
            persistence_available = self._database_persistence_available()
            latest = self._load_database_latest() if persistence_available else None
            return ScannerStatusResponse(
                scanner_ready=persistence_available,
                mode="database",
                universe_source="database",
                data_available=True,
                latest_scan_available=latest is not None,
                last_scan_at=None if latest is None else latest.generated_at,
                qualified_rule="A+ and A only",
                watch_rule="B+ watch only",
                execution_enabled=False,
            )

        if self._production:
            return self._no_data_status()

        data_available = self._ohlc_cache.get_status().data_available
        if not data_available:
            return self._no_data_status()

        latest = self._scanner_repository.load()
        return ScannerStatusResponse(
            scanner_ready=True,
            mode="local_csv",
            universe_source="local_csv",
            data_available=True,
            latest_scan_available=latest is not None,
            last_scan_at=None if latest is None else latest.generated_at,
            qualified_rule="A+ and A only",
            watch_rule="B+ watch only",
            execution_enabled=False,
        )

    def load_latest(self) -> ScannerResultResponse | None:
        """Load the authoritative persisted scanner result for this runtime."""

        if self._production:
            return self._load_database_latest()

        database_latest = self._load_database_latest()
        if database_latest is not None:
            return database_latest
        return self._scanner_repository.load()

    def run(self) -> ScannerResultResponse:
        """Run the scanner fail-closed using only the approved Phase-1 universe."""

        if self._scanner_engine is None:
            raise RuntimeError("Scanner execution engine is not configured.")

        source, rows = self._load_active_rows()
        if not rows:
            message = (
                "No verified database OHLC data is available for the production scanner."
                if self._production
                else "No approved DSE OHLC data is available. Import verified OHLC data first."
            )
            return self._no_data_result(message)

        source_symbols = {row.symbol for row in rows}
        approved_rows = [row for row in rows if row.symbol in PHASE1_SYMBOLS]
        approved_symbols = source_symbols & PHASE1_SYMBOLS
        out_of_scope_count = len(source_symbols - PHASE1_SYMBOLS)

        if not approved_rows:
            return ScannerResultResponse(
                ok=False,
                mode=source,
                data_source=source,
                scanned_symbols=len(source_symbols),
                eligible_symbols=0,
                qualified_count=0,
                watch_count=0,
                rejected_count=0,
                generated_at=None,
                message=(
                    "The active OHLC source contains no approved Phase-1 symbols. "
                    f"{out_of_scope_count} out-of-scope symbol(s) were excluded fail-closed."
                ),
                candidates=[],
            )

        result = self._scanner_engine.run(approved_rows, source=source)
        result.scanned_symbols = len(source_symbols)
        result.message = (
            f"Phase-1 scanner evaluated {len(approved_symbols)} approved symbol(s). "
            f"{out_of_scope_count} out-of-scope symbol(s) were excluded fail-closed. "
            + result.message
        )

        if result.eligible_symbols == 0:
            result.ok = False
            result.generated_at = None
            result.candidates = []
            result.message = (
                "Scanner execution failed closed because no approved symbol had the "
                "minimum 60 verified OHLC rows. "
                + result.message
            )
            return result

        if source == "database":
            if self._database_scanner_repository is None or not self._database_scanner_repository.save(result):
                return ScannerResultResponse(
                    ok=False,
                    mode="database",
                    data_source="database",
                    scanned_symbols=result.scanned_symbols,
                    eligible_symbols=result.eligible_symbols,
                    qualified_count=result.qualified_count,
                    watch_count=result.watch_count,
                    rejected_count=result.rejected_count,
                    generated_at=None,
                    message=(
                        "Scanner calculation completed but database persistence failed; "
                        "the result was rejected fail-closed."
                    ),
                    candidates=[],
                )
        else:
            self._scanner_repository.save(result)

        return result

    def _load_active_rows(self) -> tuple[str, list]:
        if self._database_data_available() and self._database_ohlc_repository is not None:
            if not self._database_persistence_available():
                return "database", []
            return "database", self._database_ohlc_repository.get_all_rows()

        if self._production:
            return "database", []

        return "local_csv", self._ohlc_cache.get_all_rows()

    def _database_data_available(self) -> bool:
        if self._database_ohlc_repository is None:
            return False
        return self._database_ohlc_repository.get_status().data_available

    def _database_persistence_available(self) -> bool:
        return (
            self._database_scanner_repository is not None
            and self._database_scanner_repository.is_available()
        )

    def _load_database_latest(self) -> ScannerResultResponse | None:
        if not self._database_persistence_available() or self._database_scanner_repository is None:
            return None
        return self._database_scanner_repository.load_latest()

    @staticmethod
    def _no_data_status() -> ScannerStatusResponse:
        return ScannerStatusResponse(
            scanner_ready=False,
            mode="no_data",
            universe_source="none",
            data_available=False,
            latest_scan_available=False,
            last_scan_at=None,
            qualified_rule="A+ and A only",
            watch_rule="B+ watch only",
            execution_enabled=False,
        )

    @staticmethod
    def _no_data_result(message: str) -> ScannerResultResponse:
        return ScannerResultResponse(
            ok=False,
            mode="no_data",
            data_source="none",
            scanned_symbols=0,
            eligible_symbols=0,
            qualified_count=0,
            watch_count=0,
            rejected_count=0,
            generated_at=None,
            message=message,
            candidates=[],
        )
