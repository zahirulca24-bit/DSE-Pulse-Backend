"""Scanner status route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.scanner import ScannerStatusResponse
from app.services.dependencies import (
    get_ohlc_db_repository,
    get_ohlc_repository,
    get_scanner_db_repository,
    get_scanner_repository,
)
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status", response_model=ScannerStatusResponse)
def get_scanner_status(
    database_ohlc: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    local_ohlc: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    database_scanner: Annotated[ScannerDbRepository, Depends(get_scanner_db_repository)],
    local_scanner: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> ScannerStatusResponse:
    return ScannerService(database_ohlc, local_ohlc, database_scanner, local_scanner).get_status()
