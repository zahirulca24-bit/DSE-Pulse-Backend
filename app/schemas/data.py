"""CSV ingestion and data status schemas."""

from datetime import date, datetime
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


class DataAuditResponse(BaseModel):
    """Database OHLC integrity and scanner-readiness summary."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    data_source: Literal["database", "none"]
    rows_count: int
    symbols_count: int
    earliest_trade_date: date | None
    latest_trade_date: date | None
    duplicate_symbol_date_rows: int
    zero_volume_rows: int
    non_positive_price_rows: int
    invalid_ohlc_rows: int
    symbols_with_fewer_than_60_rows: int
    latest_date_symbols_count: int
    latest_date_coverage_percent: float
    stale_symbols_count: int
    scanner_ready: bool
    warnings: list[str]
    audited_at: datetime


class StaleSymbolItem(BaseModel):
    """One symbol whose latest row predates the dataset latest trade date."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    latest_trade_date: date
    rows_count: int
    lag_days: int


class StaleSymbolsResponse(BaseModel):
    """Detailed stale-symbol list for data-gap and suspension review."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    data_source: Literal["database", "none"]
    dataset_latest_trade_date: date | None
    count: int
    symbols: list[StaleSymbolItem]
    message: str
    audited_at: datetime
