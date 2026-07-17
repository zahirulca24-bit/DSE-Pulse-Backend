"""Health endpoint schema."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Lightweight process health response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    app: str
    version: str
    mode: str
    market: Literal["DSE"]
    market_open_now: bool
