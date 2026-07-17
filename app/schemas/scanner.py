"""Scanner readiness schema."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScannerStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scanner_ready: bool
    mode: Literal["database", "local_csv", "no_data"]
    universe_source: Literal["database", "local_csv", "none"]
    data_available: bool
    latest_scan_available: bool
    last_scan_at: datetime | None
    qualified_rule: Literal["A+ and A only"]
    watch_rule: Literal["B+ watch only"]
    execution_enabled: bool
