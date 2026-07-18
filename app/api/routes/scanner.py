"""Scanner status route for the approved Drive-backed cache path."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.scanner import ScannerStatusResponse
from app.services.dependencies import get_scanner_service
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status", response_model=ScannerStatusResponse)
def get_scanner_status(
    service: Annotated[ScannerService, Depends(get_scanner_service)],
) -> ScannerStatusResponse:
    return service.get_status()
