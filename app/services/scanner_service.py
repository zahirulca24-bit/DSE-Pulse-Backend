"""Scanner readiness service for the approved Drive-backed local cache path."""

from app.schemas.scanner import ScannerStatusResponse
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository


class ScannerService:
    def __init__(
        self,
        ohlc_cache: OhlcRepository,
        scanner_repository: ScannerRepository,
    ) -> None:
        self._ohlc_cache = ohlc_cache
        self._scanner_repository = scanner_repository

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
