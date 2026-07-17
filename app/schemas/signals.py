"""Demo signal response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus

EntryStatus = Literal["READY", "WATCH", "NOT_READY"]


class SignalItem(BaseModel):
    """A deterministic non-executable demo signal item."""

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
    """Collection of deterministic local demo signals and public rules."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["demo"]
    data_source: Literal["demo"]
    signals: list[SignalItem]
    rules: dict[str, str]
