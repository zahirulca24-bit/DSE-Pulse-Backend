"""OHLC row and query response schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OhlcRow(BaseModel):
    """A normalized DSE OHLC row."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    trade_date: date
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: int = Field(ge=0)
    trade: float | None = None
    value: float | None = None


class SymbolsResponse(BaseModel):
    """Available symbols from the stored local CSV."""

    model_config = ConfigDict(extra="forbid")

    data_source: Literal["none", "local_csv"]
    symbols_count: int
    symbols: list[str]


class OhlcResponse(BaseModel):
    """Filtered OHLC rows for one symbol."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    data_source: Literal["none", "local_csv"]
    rows_count: int
    rows: list[OhlcRow]
