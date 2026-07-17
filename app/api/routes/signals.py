"""Demo fallback and latest scanner signal route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.signals import SignalsResponse
from app.services.dependencies import get_scanner_repository
from app.services.scanner_repository import ScannerRepository
from app.services.signal_service import SignalService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
def get_signals(repository: Annotated[ScannerRepository, Depends(get_scanner_repository)]) -> SignalsResponse:
    return SignalService(repository).get_signals()
