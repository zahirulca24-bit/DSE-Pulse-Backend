"""Stored local OHLC query route."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.schemas.ohlc import OhlcResponse
from app.services.dependencies import get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["ohlc"])


@router.get("/ohlc/{symbol}", response_model=OhlcResponse)
def get_symbol_ohlc(
    symbol: str,
    repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> OhlcResponse:
    """Return local OHLC rows sorted newest first without generating fallback data."""

    return repository.get_ohlc(symbol, limit, start_date, end_date)
