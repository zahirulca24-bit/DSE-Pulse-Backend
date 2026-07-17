"""Scanner readiness service with database/local fallback."""

from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.scanner import ScannerStatusResponse
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository


class ScannerService:
    def __init__(
        self,
        database_ohlc: OhlcDbRepository,
        local_ohlc: OhlcRepository,
        database_scanner: ScannerDbRepository,
        local_scanner: ScannerRepository,
    ) -> None:
        self._database_ohlc = database_ohlc
        self._local_ohlc = local_ohlc
        self._database_scanner = database_scanner
        self._local_scanner = local_scanner

    def get_status(self) -> ScannerStatusResponse:
        if self._database_ohlc.is_available():
            mode = "database"
            source = "database"
            data_available = True
        elif self._local_ohlc.get_status().data_available:
            mode = "local_csv"
            source = "local_csv"
            data_available = True
        else:
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
        latest = self._database_scanner.load_latest() or self._local_scanner.load()
        return ScannerStatusResponse(
            scanner_ready=True,
            mode=mode,
            universe_source=source,
            data_available=data_available,
            latest_scan_available=latest is not None,
            last_scan_at=None if latest is None else latest.generated_at,
            qualified_rule="A+ and A only",
            watch_rule="B+ watch only",
            execution_enabled=False,
        )
