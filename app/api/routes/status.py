"""Backend integration status route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.schemas.status import BackendStatusResponse
from app.services.dependencies import get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["status"])


@router.get("/status", response_model=BackendStatusResponse)
def get_status(
    repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
) -> BackendStatusResponse:
    """Return truthful integration status and real local CSV counts when available."""

    settings = get_settings()
    data_status = repository.get_status()
    if data_status.data_available:
        data_source = "local_csv"
        message = "Backend is running with local CSV data."
    else:
        data_source = "demo"
        message = "Backend is running in demo/local-only mode."

    return BackendStatusResponse(
        status="ok",
        mode=settings.app_mode,
        data_source=data_source,
        backend_ready=True,
        database_connected=False,
        live_market_connected=False,
        broker_connected=False,
        last_data_date=data_status.latest_trade_date,
        symbols_count=data_status.symbols_count,
        rows_count=data_status.rows_count,
        message=message,
    )
