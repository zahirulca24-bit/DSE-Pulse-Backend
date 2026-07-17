"""Deterministic demo signal service."""

from app.core.signal_rules import classify_score, public_signal_rules
from app.data.demo_candidates import DEMO_CANDIDATES
from app.schemas.signals import EntryStatus, SignalItem, SignalsResponse


class SignalService:
    """Build API responses from local deterministic candidates."""

    @staticmethod
    def _entry_status(signal_status: str) -> EntryStatus:
        if signal_status == "qualified":
            return "READY"
        if signal_status == "watch":
            return "WATCH"
        return "NOT_READY"

    def get_demo_signals(self) -> SignalsResponse:
        """Return stable demo signals with no external dependency."""

        signals: list[SignalItem] = []
        for candidate in DEMO_CANDIDATES:
            grade, signal_status = classify_score(candidate.score)
            signals.append(
                SignalItem(
                    symbol=candidate.symbol,
                    company=candidate.company,
                    sector=candidate.sector,
                    grade=grade,
                    score=candidate.score,
                    signal_status=signal_status,
                    entry_status=self._entry_status(signal_status),
                    risk_reward=candidate.risk_reward,
                    reasons=["Demo technical setup only"],
                    warnings=[],
                    data_mode="Demo Data",
                )
            )

        return SignalsResponse(
            mode="demo",
            data_source="demo",
            signals=signals,
            rules=public_signal_rules(),
        )
