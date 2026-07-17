"""Schemas for manual DSE data collection jobs."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


CollectorStatus = Literal["queued", "running", "completed", "failed"]


class CollectorRunRequest(BaseModel):
    """Target date and safe missing-date backfill preference."""

    model_config = ConfigDict(extra="forbid")

    trade_date: date | None = None
    collect_missing: bool = True


class CollectorRunResponse(BaseModel):
    """Sanitized persisted collector job state."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: CollectorStatus
    requested_trade_date: date
    source: str
    fetched_rows: int
    collected_symbols: int
    inserted_rows: int
    updated_rows: int
    invalid_rows: int
    missing_symbols: list[str]
    warnings: list[str]
    error_message: str | None
    scanner_refresh_required: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CollectorHistoryResponse(BaseModel):
    """Recent collector jobs."""

    model_config = ConfigDict(extra="forbid")

    count: int
    jobs: list[CollectorRunResponse]
