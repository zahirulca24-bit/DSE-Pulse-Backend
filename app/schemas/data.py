"""CSV ingestion and data status schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.ohlc import OhlcRow


class DataPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mode: Literal["local_preview"]
    filename: str
    detected_headers: list[str]
    normalized_headers: list[str]
    valid_rows: int
    invalid_rows: int
    symbols_count: int
    latest_trade_date: date | None
    preview_rows: list[OhlcRow]
    warnings: list[str]
    errors: list[str]


class DataImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mode: Literal["local_csv"]
    stored_path: str
    valid_rows: int
    invalid_rows: int
    symbols_count: int
    latest_trade_date: date | None
    message: str
    warnings: list[str]
    errors: list[str]


class DataStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_available: bool
    data_source: Literal["database", "local_csv", "none"]
    stored_path: str | None
    symbols_count: int | None
    rows_count: int | None
    latest_trade_date: date | None
    earliest_trade_date: date | None
    message: str
