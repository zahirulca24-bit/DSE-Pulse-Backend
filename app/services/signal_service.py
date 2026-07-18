"""Return only real signals from the approved cache-backed scanner result."""

from app.core.signal_rules import public_signal_rules
from app.schemas.signals import SignalsResponse
from app.services.scanner_repository import ScannerRepository


class SignalService:
    def __init__(self, repository: ScannerRepository) -> None:
        self._repository = repository

    def get_signals(self) -> SignalsResponse:
        latest = self._repository.load()

        if latest is not None and latest.ok:
            candidates = [
                item
                for item in latest.candidates
                if (
                    item.signal_status == "qualified"
                    and item.qualification_passed
                    and item.grade in {"A+", "A"}
                )
                or (item.signal_status == "watch" and item.grade == "B+")
            ]
            return SignalsResponse(
                mode=latest.mode,
                data_source=latest.data_source,
                signals=candidates,
                rules=public_signal_rules(),
                message="Latest persisted scanner signals returned after strict qualification gates.",
            )

        return SignalsResponse(
            mode="no_scan",
            data_source="none",
            signals=[],
            rules=public_signal_rules(),
            message="No real scanner result exists yet. Run the scanner with verified OHLC data first.",
        )
