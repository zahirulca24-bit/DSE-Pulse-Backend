"""Scanner readiness and execution service for the approved Drive-backed cache path."""

from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.schemas.scanner import ScannerStatusResponse
from app.schemas.scanner_result import ScannerResultResponse
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository


class ScannerService:
    """Single production scanner path shared by manual and scheduled execution."""

    def __init__(
        self,
        ohlc_cache: OhlcRepository,
        scanner_repository: ScannerRepository,
        scanner_engine: ScannerEngine | None = None,
    ) -> None:
        self._ohlc_cache = ohlc_cache
        self._scanner_repository = scanner_repository
        self._scanner_engine = scanner_engine

    def get_status(self) -> ScannerStatusResponse:
        data_available = self._ohlc_cache.get_status().data_available
        if not data_available:
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

    def run(self) -> ScannerResultResponse:
        """Run the scanner fail-closed using only the approved Phase-1 universe."""

        if self._scanner_engine is None:
            raise RuntimeError("Scanner execution engine is not configured.")

        rows = self._ohlc_cache.get_all_rows()
        if not rows:
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
                message=(
                    "No approved DSE OHLC cache is available. "
                    "Import/sync verified OHLC data through the Google Drive storage pipeline first."
                ),
                candidates=[],
            )

        source_symbols = {row.symbol for row in rows}
        approved_rows = [row for row in rows if row.symbol in PHASE1_SYMBOLS]
        approved_symbols = source_symbols & PHASE1_SYMBOLS
        out_of_scope_count = len(source_symbols - PHASE1_SYMBOLS)

        if not approved_rows:
            return ScannerResultResponse(
                ok=False,
                mode="no_data",
                data_source="none",
                scanned_symbols=len(source_symbols),
                eligible_symbols=0,
                qualified_count=0,
                watch_count=0,
                rejected_count=0,
                generated_at=None,
                message=(
                    "The OHLC cache contains no approved Phase-1 symbols. "
                    f"{out_of_scope_count} out-of-scope symbol(s) were excluded fail-closed."
                ),
                candidates=[],
            )

        result = self._scanner_engine.run(approved_rows, source="local_csv")
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

        self._scanner_repository.save(result)
        return result
