"""Scanner readiness schema."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScannerStatusResponse(BaseModel):
    """Scanner readiness without claiming an active worker or execution layer."""

    model_config = ConfigDict(extra="forbid")

    scanner_ready: bool
    mode: str
    universe_source: Literal["demo"]
    last_scan_at: datetime | None
    qualified_rule: Literal["A+ and A only"]
    watch_rule: Literal["B+ watch only"]
    execution_enabled: bool
