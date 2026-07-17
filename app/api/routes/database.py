"""Optional database connection and initialization routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.database import DatabaseManager
from app.db.init_db import initialize_database
from app.schemas.database import DatabaseInitResponse, DatabaseStatusResponse
from app.services.dependencies import get_database_manager

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/status", response_model=DatabaseStatusResponse)
def get_database_status(
    manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> DatabaseStatusResponse:
    """Return a safe connection summary without exposing credentials."""

    status = manager.get_status()
    return DatabaseStatusResponse(
        configured=status.configured,
        connected=status.connected,
        database_type="postgres",
        message=status.message,
    )


@router.post("/init", response_model=DatabaseInitResponse)
def init_database_tables(
    manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> DatabaseInitResponse:
    """Create missing tables only; never drop or truncate existing data."""

    status = manager.get_status()
    if not status.configured:
        return DatabaseInitResponse(ok=False, message="DATABASE_URL is not configured.")
    if not status.connected:
        return DatabaseInitResponse(ok=False, message="Database connection is unavailable.")
    if not initialize_database(manager):
        return DatabaseInitResponse(ok=False, message="Database tables could not be initialized.")
    return DatabaseInitResponse(ok=True, message="Database tables initialized.")
