"""Optional database connection and initialization routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.database import DatabaseManager
from app.db.init_db import initialize_database
from app.schemas.database import DatabaseInitResponse, DatabaseStatusResponse
from app.security.admin import require_backend_admin
from app.services.dependencies import get_database_manager

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/status", response_model=DatabaseStatusResponse)
def get_database_status(
    manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> DatabaseStatusResponse:
    """Return a safe connection summary without exposing credentials."""

    status_result = manager.get_status()
    return DatabaseStatusResponse(
        configured=status_result.configured,
        connected=status_result.connected,
        database_type="postgres",
        message=status_result.message,
    )


@router.post(
    "/init",
    response_model=DatabaseInitResponse,
    dependencies=[Depends(require_backend_admin)],
)
def init_database_tables(
    manager: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> DatabaseInitResponse:
    """Create missing tables only after backend administrator authorization."""

    connection = manager.get_status()
    if not connection.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured.",
        )
    if not connection.connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        )
    if not initialize_database(manager):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database tables could not be initialized.",
        )
    return DatabaseInitResponse(ok=True, message="Database tables initialized.")
