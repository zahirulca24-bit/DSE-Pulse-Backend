"""Scanner readiness service."""

from app.schemas.scanner import ScannerStatusResponse
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository


class ScannerService:
    def __init__(self, ohlc_repository: OhlcRepository, scanner_repository: ScannerRepository) -> None:
        self._ohlc = ohlc_repository
        self._scanner = scanner_repository

    def get_status(self) -> ScannerStatusResponse:
        data_status = self._ohlc.get_status()
        if not data_status.data_available:
            return ScannerStatusResponse(scanner_ready=False, mode="no_data", universe_source="none",
                data_available=False, latest_scan_available=False, last_scan_at=None,
                qualified_rule="A+ and A only", watch_rule="B+ watch only", execution_enabled=False)
        latest = self._scanner.load()
        return ScannerStatusResponse(scanner_ready=True, mode="local_csv", universe_source="local_csv",
            data_available=True, latest_scan_available=latest is not None,
            last_scan_at=None if latest is None else latest.generated_at,
            qualified_rule="A+ and A only", watch_rule="B+ watch only", execution_enabled=False)
