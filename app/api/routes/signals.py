"""Deterministic demo signal route."""

from fastapi import APIRouter

from app.schemas.signals import SignalsResponse
from app.services.signal_service import SignalService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
def get_signals() -> SignalsResponse:
    """Return deterministic local demo signals only."""

    return SignalService().get_demo_signals()
