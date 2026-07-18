"""Return only persisted real scanner signals; never fabricate demo signals."""

from app.core.signal_rules import public_signal_rules
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.signals import SignalsResponse
from app.services.scanner_repository import ScannerRepository


class SignalService:
    def __init__(
        self,
        database_repository: ScannerDbRepository,
        local_repository: ScannerRepository,
    ) -> None:
        self._database_repository = database_repository
        self._local_repository = local_repository

    def get_signals(self) -> SignalsResponse:
        latest = self._database_repository.load_latest()
        if latest is None:
            latest = self._local_repository.load()

        if latest is not None and latest.ok:
            candidates = [
                item
                for item in latest.candidates
                if item.signal_status in {"qualified", "watch"}
            ]
            return SignalsResponse(
                mode=latest.mode,
                data_source=latest.data_source,
                signals=candidates,
                rules=public_signal_rules(),
                message="Latest persisted scanner signals returned.",
            )

        return SignalsResponse(
            mode="no_scan",
            data_source="none",
            signals=[],
            rules=public_signal_rules(),
            message="No real scanner result exists yet. Run the scanner with verified OHLC data first.",
        )
