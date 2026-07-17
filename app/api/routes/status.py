"""Backend integration status route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.db.database import DatabaseManager
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.status import BackendStatusResponse
from app.services.dependencies import get_database_manager, get_ohlc_db_repository, get_ohlc_repository
from app.services.ohlc_repository import OhlcRepository

router = APIRouter(tags=["status"])


@router.get("/status", response_model=BackendStatusResponse)
def get_status(
    local_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    database_repository: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    database_manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> BackendStatusResponse:
    """Return database data when available, otherwise preserve local/demo fallback."""

    settings = get_settings()
    database_status = database_manager.get_status()
    if database_repository.is_available():
        data = database_repository.get_status()
        source = "database"
        message = data.message
    else:
        data = local_repository.get_status()
        if data.data_available:
            source = "local_csv"
            message = "Backend is running with local CSV data."
        else:
            source = "demo"
            message = "Backend is running in demo/local-only mode."
    return BackendStatusResponse(
        status="ok",
        mode=settings.app_mode,
        data_source=source,
        backend_ready=True,
        database_connected=database_status.connected,
        live_market_connected=False,
        broker_connected=False,
        last_data_date=data.latest_trade_date,
        symbols_count=data.symbols_count,
        rows_count=data.rows_count,
        message=message,
    )
