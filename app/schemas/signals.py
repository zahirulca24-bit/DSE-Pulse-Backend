"""Demo and local scanner signal response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus
from app.schemas.scanner_result import ScannerCandidate

EntryStatus = Literal["READY", "WATCH", "NOT_READY"]


class SignalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company: str
    sector: SectorName
    grade: SignalGrade
    score: int = Field(ge=0, le=100)
    signal_status: SignalStatus
    entry_status: EntryStatus
    risk_reward: float = Field(gt=0)
    reasons: list[str]
    warnings: list[str]
    data_mode: Literal["Demo Data"]


class SignalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["demo", "local_csv"]
    data_source: Literal["demo", "local_csv"]
    signals: list[SignalItem | ScannerCandidate]
    rules: dict[str, str]
