"""CSV preview, import, and local data status schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.ohlc import OhlcRow


class DataPreviewResponse(BaseModel):
    """Validation result for an uploaded CSV that is not saved."""

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
    """Result of validating and saving normalized valid rows locally."""

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
    """Current local CSV availability and derived metadata."""

    model_config = ConfigDict(extra="forbid")

    data_available: bool
    data_source: Literal["none", "local_csv"]
    stored_path: str | None
    symbols_count: int | None
    rows_count: int | None
    latest_trade_date: date | None
    earliest_trade_date: date | None
    message: str
