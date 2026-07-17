"""Scanner readiness service for the API-foundation phase."""

from app.core.config import Settings
from app.schemas.scanner import ScannerStatusResponse


class ScannerService:
    """Report scanner readiness without running a worker or external scan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_status(self) -> ScannerStatusResponse:
        """Return the safe, non-executing scanner state."""

        return ScannerStatusResponse(
            scanner_ready=True,
            mode=self._settings.app_mode,
            universe_source="demo",
            last_scan_at=None,
            qualified_rule="A+ and A only",
            watch_rule="B+ watch only",
            execution_enabled=False,
        )
