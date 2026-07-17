"""Scanner run, candidate, and latest-result schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus

ScannerMode = Literal["database", "local_csv", "no_data", "no_scan"]
SetupType = Literal[
    "EMA Trend Pullback",
    "20-Day Breakout",
    "RSI Momentum Recovery",
    "SMA Trend Continuation",
    "Rejected / No Setup",
]
TrendType = Literal["BULLISH", "BEARISH", "NEUTRAL"]
EntryStatus = Literal["READY", "WATCH", "NOT_READY"]


class ScannerCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company: None = None
    sector: SectorName | None
    grade: SignalGrade
    score: int = Field(ge=0, le=100)
    signal_status: SignalStatus
    entry_status: EntryStatus
    setup: SetupType
    latest_close: float = Field(ge=0)
    trade_date: date
    trend: TrendType
    ema20: float
    ema50: float
    sma20: float
    sma50: float
    rsi14: float
    volume_ratio: float = Field(ge=0)
    risk_reward: float = Field(ge=0)
    reasons: list[str]
    warnings: list[str]
    data_mode: Literal["Database", "Local CSV"]


class ScannerResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mode: ScannerMode
    data_source: Literal["database", "local_csv", "none"]
    scanned_symbols: int
    eligible_symbols: int
    qualified_count: int
    watch_count: int
    rejected_count: int
    generated_at: datetime | None
    message: str
    candidates: list[ScannerCandidate]


class ScannerCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mode: ScannerMode
    data_source: Literal["database", "local_csv", "none"]
    message: str
    candidates_count: int
    candidates: list[ScannerCandidate]
