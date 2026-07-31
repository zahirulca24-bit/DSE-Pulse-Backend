from datetime import UTC, date, datetime
from pathlib import Path

from app.db.database import DatabaseManager
from app.db.models import Base
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.scanner_result import ScannerCandidate, ScannerResultResponse


def test_scanner_db_preserves_candidate_state_and_deduplicates(tmp_path: Path) -> None:
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'scanner.db'}")
    assert manager.engine is not None
    Base.metadata.create_all(manager.engine)
    repository = ScannerDbRepository(manager)

    candidate = ScannerCandidate(
        symbol="BRACBANK",
        company=None,
        sector="Bank",
        grade="A",
        score=92,
        signal_status="qualified",
        entry_status="READY",
        setup="EMA Trend Pullback",
        latest_close=48.5,
        trade_date=date(2026, 7, 30),
        trend="BULLISH",
        ema20=48.0,
        ema50=46.0,
        sma20=47.8,
        sma50=45.9,
        rsi14=59.0,
        volume_ratio=1.8,
        risk_reward=1.75,
        qualification_passed=True,
        qualification_failures=[],
        entry_distance_percent=1.04,
        reasons=["Qualification passed."],
        warnings=[],
        data_mode="Database",
    )
    result = ScannerResultResponse(
        ok=True,
        mode="database",
        data_source="database",
        scanned_symbols=1,
        eligible_symbols=1,
        qualified_count=1,
        watch_count=0,
        rejected_count=0,
        generated_at=datetime.now(UTC),
        message="Completed.",
        candidates=[candidate, candidate.model_copy(update={"symbol": "bracbank"})],
    )

    assert repository.save(result) is True
    loaded = repository.load_latest()
    assert loaded is not None
    assert len(loaded.candidates) == 1
    saved = loaded.candidates[0]
    assert saved.symbol == "BRACBANK"
    assert saved.qualification_passed is True
    assert saved.qualification_failures == []
    assert saved.entry_distance_percent == 1.04
