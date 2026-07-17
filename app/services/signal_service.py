"""Database/local scanner signals with deterministic demo fallback."""

from app.core.signal_rules import classify_score, public_signal_rules
from app.data.demo_candidates import DEMO_CANDIDATES
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.signals import SignalItem, SignalsResponse
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
            candidates = [item for item in latest.candidates if item.signal_status in {"qualified", "watch"}]
            return SignalsResponse(
                mode=latest.mode,
                data_source=latest.data_source,
                signals=candidates,
                rules=public_signal_rules(),
            )
        return self.get_demo_signals()

    @staticmethod
    def get_demo_signals() -> SignalsResponse:
        signals: list[SignalItem] = []
        for candidate in DEMO_CANDIDATES:
            grade, status = classify_score(candidate.score)
            entry_status = "READY" if status == "qualified" else "WATCH" if status == "watch" else "NOT_READY"
            signals.append(
                SignalItem(
                    symbol=candidate.symbol,
                    company=candidate.company,
                    sector=candidate.sector,
                    grade=grade,
                    score=candidate.score,
                    signal_status=status,
                    entry_status=entry_status,
                    risk_reward=candidate.risk_reward,
                    reasons=["Demo technical setup only"],
                    warnings=[],
                    data_mode="Demo Data",
                )
            )
        return SignalsResponse(mode="demo", data_source="demo", signals=signals, rules=public_signal_rules())
