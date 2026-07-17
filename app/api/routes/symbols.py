"""Symbol list route with database-first fallback."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.ohlc import SymbolsResponse
from app.services.dependencies import get_ohlc_db_repository, get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["symbols"])


@router.get("/symbols", response_model=SymbolsResponse)
def get_symbols(
    database_repository: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    local_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
) -> SymbolsResponse:
    """Return database symbols when its table is available, otherwise local symbols."""

    if database_repository.is_available():
        return database_repository.get_symbols()
    return local_repository.get_symbols()
