"""Backend status endpoint schema."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BackendStatusResponse(BaseModel):
    """Truthful integration readiness summary."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    mode: str
    data_source: Literal["demo"]
    backend_ready: bool
    database_connected: bool
    live_market_connected: bool
    broker_connected: bool
    last_data_date: date | None
    symbols_count: int | None
    rows_count: int | None
    message: str
