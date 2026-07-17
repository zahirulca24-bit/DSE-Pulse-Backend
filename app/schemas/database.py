"""Optional database API schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DatabaseStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    connected: bool
    database_type: Literal["postgres"]
    message: str


class DatabaseInitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str


class DatabaseImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    data_source: Literal["database"]
    inserted_rows: int
    updated_rows: int
    invalid_rows: int
    symbols_count: int
    latest_trade_date: date | None
    message: str


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_source: Literal["database", "local_csv", "demo"]
    database_available: bool
    local_csv_available: bool
    fallback_order: list[Literal["database", "local_csv", "demo"]]
