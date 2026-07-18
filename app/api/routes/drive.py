"""Google Drive storage readiness route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.drive import DriveStatusResponse
from app.services.dependencies import get_drive_ohlc_repository
from app.services.drive_ohlc_repository import DriveOhlcRepository

router = APIRouter(prefix="/drive", tags=["drive"])


@router.get("/status", response_model=DriveStatusResponse)
def get_drive_status(
    repository: Annotated[DriveOhlcRepository, Depends(get_drive_ohlc_repository)],
) -> DriveStatusResponse:
    status = repository.drive_status()
    return DriveStatusResponse(
        configured=status.configured,
        connected=status.connected,
        storage_type="google_drive",
        folder_name=status.folder_name,
        master_filename=repository.master_filename,
        message=status.message,
    )
