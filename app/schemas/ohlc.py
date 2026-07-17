"""OHLC read schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OhlcRow(BaseModel):
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
    data_source: Literal["database", "local_csv", "none"]
    symbols_count: int
    symbols: list[str]


class OhlcResponse(BaseModel):
    symbol: str
    data_source: Literal["database", "local_csv", "none"]
    rows_count: int
    rows: list[OhlcRow]
