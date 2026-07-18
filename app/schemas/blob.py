"""Vercel Blob storage API schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BlobStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    connected: bool
    storage_type: Literal["vercel_blob"]
    master_pathname: str
    message: str


class BlobImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    data_source: Literal["vercel_blob"]
    inserted_rows: int
    updated_rows: int
    invalid_rows: int
    symbols_count: int
    rows_count: int
    earliest_trade_date: date | None
    latest_trade_date: date | None
    master_pathname: str
    message: str
