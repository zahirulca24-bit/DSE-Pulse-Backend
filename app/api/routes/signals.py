"""Persisted real scanner signals only; no demo fallback."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.signals import SignalsResponse
from app.services.dependencies import get_scanner_db_repository, get_scanner_repository
from app.services.scanner_repository import ScannerRepository
from app.services.signal_service import SignalService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
def get_signals(
    database_repository: Annotated[ScannerDbRepository, Depends(get_scanner_db_repository)],
    local_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> SignalsResponse:
    return SignalService(database_repository, local_repository).get_signals()
