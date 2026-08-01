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
    rejected_rows: int = 0
    duplicate_rows: int = 0
    invalid_rows: int
    symbols_count: int
    latest_trade_date: date | None
    message: str


class DataSourceResponse(BaseModel):
    """Fail-closed active market-data source selection."""

    model_config = ConfigDict(extra="forbid")

    preferred_source: Literal["database", "local_csv", "none"]
    database_available: bool
    local_csv_available: bool
    market_data_available: bool
    fallback_order: list[Literal["database", "local_csv"]]
    message: str
