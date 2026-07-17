"""Scanner readiness route."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.scanner import ScannerStatusResponse
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status", response_model=ScannerStatusResponse)
def get_scanner_status() -> ScannerStatusResponse:
    """Return scanner readiness without starting background activity."""

    return ScannerService(get_settings()).get_status()
