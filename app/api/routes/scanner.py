"""Scanner status route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.scanner import ScannerStatusResponse
from app.services.dependencies import get_ohlc_repository, get_scanner_repository
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status", response_model=ScannerStatusResponse)
def get_scanner_status(
    ohlc_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    scanner_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> ScannerStatusResponse:
    return ScannerService(ohlc_repository, scanner_repository).get_status()
