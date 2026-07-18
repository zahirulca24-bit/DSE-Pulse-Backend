"""Scanner scheduler status schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScannerSchedulerStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    running: bool
    timezone: str
    market_window: str
    slots: list[str]
    current_slot: str | None
    next_slot_at: datetime | None
    last_slot: str | None
    last_started_at: datetime | None
    last_completed_at: datetime | None
    last_result_ok: bool | None
    last_message: str | None
