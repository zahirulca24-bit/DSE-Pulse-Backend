"""Return only real signals from the authoritative persisted scanner result."""

from app.core.signal_rules import public_signal_rules
from app.schemas.signals import SignalsResponse
from app.services.scanner_service import ScannerService


class SignalService:
    def __init__(self, scanner_service: ScannerService) -> None:
        self._scanner_service = scanner_service

    def get_signals(self) -> SignalsResponse:
        latest = self._scanner_service.load_latest()

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
