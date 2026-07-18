"""Real scanner signal response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.scanner_result import ScannerCandidate


class SignalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["database", "local_csv", "no_scan"]
    data_source: Literal["database", "local_csv", "none"]
    signals: list[ScannerCandidate]
    rules: dict[str, str]
    message: str
