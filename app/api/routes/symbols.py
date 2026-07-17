"""Stored local symbol route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.ohlc import SymbolsResponse
from app.services.dependencies import get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["symbols"])


@router.get("/symbols", response_model=SymbolsResponse)
def get_symbols(
    repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
) -> SymbolsResponse:
    """Return alphabetically sorted symbols from local CSV data only."""

    return repository.get_symbols()
