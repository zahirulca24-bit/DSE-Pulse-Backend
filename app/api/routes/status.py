"""Backend integration status route."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.status import BackendStatusResponse

router = APIRouter(tags=["status"])


@router.get("/status", response_model=BackendStatusResponse)
def get_status() -> BackendStatusResponse:
    """Return truthful demo/local-only integration status."""

    settings = get_settings()
    return BackendStatusResponse(
        status="ok",
        mode=settings.app_mode,
        data_source="demo",
        backend_ready=True,
        database_connected=False,
        live_market_connected=False,
        broker_connected=False,
        last_data_date=None,
        symbols_count=None,
        rows_count=None,
        message="Backend is running in demo/local-only mode.",
    )
