"""OHLC query route with explicit source selection."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.ohlc import OhlcResponse
from app.services.dependencies import get_ohlc_db_repository, get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["ohlc"])


@router.get("/ohlc/{symbol}", response_model=OhlcResponse)
def get_symbol_ohlc(
    symbol: str,
    database_repository: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    local_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    source: Annotated[Literal["auto", "database", "local_csv"], Query()] = "auto",
) -> OhlcResponse:
    """Use verified database rows first in auto mode, or honor an explicit source."""

    if source == "database":
        if not database_repository.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database OHLC storage is unavailable.",
            )
        return database_repository.get_ohlc(symbol, limit, start_date, end_date)
    if source == "local_csv":
        return local_repository.get_ohlc(symbol, limit, start_date, end_date)
    if database_repository.get_status().data_available:
        return database_repository.get_ohlc(symbol, limit, start_date, end_date)
    return local_repository.get_ohlc(symbol, limit, start_date, end_date)
