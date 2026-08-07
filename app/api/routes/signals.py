"""Persisted real scanner signals from the authoritative scanner path."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.signals import SignalsResponse
from app.services.dependencies import get_scanner_service
from app.services.scanner_service import ScannerService
from app.services.signal_service import SignalService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
def get_signals(
    service: Annotated[ScannerService, Depends(get_scanner_service)],
) -> SignalsResponse:
    return SignalService(service).get_signals()
