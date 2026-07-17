"""SQLAlchemy repository for optional latest scanner persistence."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import ScannerCandidateRecord, ScannerRun
from app.schemas.scanner_result import ScannerCandidate, ScannerResultResponse


class ScannerDbRepository:
    """Save and load final scanner runs through SQLAlchemy."""

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager

    def is_available(self) -> bool:
        return self._manager.has_tables(("scanner_runs", "scanner_candidates"))

    def save(self, result: ScannerResultResponse) -> bool:
        if not self.is_available() or result.generated_at is None:
            return False
        run_id = str(uuid4())
        try:
            with self._manager.session() as session:
                session.add(
                    ScannerRun(
                        run_id=run_id,
                        mode="database",
                        data_source="database",
                        scanned_symbols=result.scanned_symbols,
                        eligible_symbols=result.eligible_symbols,
                        qualified_count=result.qualified_count,
                        watch_count=result.watch_count,
                        rejected_count=result.rejected_count,
                        generated_at=result.generated_at,
                    )
                )
                for candidate in result.candidates[:50]:
                    session.add(
                        ScannerCandidateRecord(
                            run_id=run_id,
                            symbol=candidate.symbol,
                            company=candidate.company,
                            sector=candidate.sector,
                            grade=candidate.grade,
                            score=candidate.score,
                            signal_status=candidate.signal_status,
                            entry_status=candidate.entry_status,
                            setup=candidate.setup,
                            latest_close=candidate.latest_close,
                            trade_date=candidate.trade_date,
                            trend=candidate.trend,
                            ema20=candidate.ema20,
                            ema50=candidate.ema50,
                            sma20=candidate.sma20,
                            sma50=candidate.sma50,
                            rsi14=candidate.rsi14,
                            volume_ratio=candidate.volume_ratio,
                            risk_reward=candidate.risk_reward,
                            reasons_json=candidate.reasons,
                            warnings_json=candidate.warnings,
                            data_mode="Database",
                        )
                    )
                session.commit()
        except (SQLAlchemyError, RuntimeError):
            return False
        return True

    def load_latest(self) -> ScannerResultResponse | None:
        if not self.is_available():
            return None
        try:
            with self._manager.session() as session:
                run = session.scalar(
                    select(ScannerRun).order_by(ScannerRun.generated_at.desc(), ScannerRun.id.desc()).limit(1)
                )
                if run is None:
                    return None
                records = list(
                    session.scalars(
                        select(ScannerCandidateRecord)
                        .where(ScannerCandidateRecord.run_id == run.run_id)
                        .order_by(ScannerCandidateRecord.id)
                        .limit(50)
                    ).all()
                )
        except (SQLAlchemyError, RuntimeError):
            return None
        candidates = [
            ScannerCandidate(
                symbol=record.symbol,
                company=None,
                sector=record.sector,
                grade=record.grade,
                score=record.score,
                signal_status=record.signal_status,
                entry_status=record.entry_status,
                setup=record.setup,
                latest_close=record.latest_close,
                trade_date=record.trade_date,
                trend=record.trend,
                ema20=record.ema20,
                ema50=record.ema50,
                sma20=record.sma20,
                sma50=record.sma50,
                rsi14=record.rsi14,
                volume_ratio=record.volume_ratio,
                risk_reward=record.risk_reward,
                reasons=list(record.reasons_json),
                warnings=list(record.warnings_json),
                data_mode="Database",
            )
            for record in records
        ]
        return ScannerResultResponse(
            ok=True,
            mode="database",
            data_source="database",
            scanned_symbols=run.scanned_symbols,
            eligible_symbols=run.eligible_symbols,
            qualified_count=run.qualified_count,
            watch_count=run.watch_count,
            rejected_count=run.rejected_count,
            generated_at=run.generated_at,
            message="Latest database scanner result returned.",
            candidates=candidates,
        )
