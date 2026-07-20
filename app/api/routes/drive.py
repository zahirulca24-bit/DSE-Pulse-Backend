"""Backward-compatible storage status route for the deployed frontend."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.drive import DriveStatusResponse
from app.services.blob_ohlc_repository import BlobOhlcRepository
from app.services.dependencies import get_blob_ohlc_repository

router = APIRouter(prefix="/drive", tags=["storage-compat"])


@router.get("/status", response_model=DriveStatusResponse)
def get_drive_status(
    repository: Annotated[BlobOhlcRepository, Depends(get_blob_ohlc_repository)],
) -> DriveStatusResponse:
    """Expose Blob readiness using the legacy response expected by the live UI."""

    status = repository.blob_status()
    return DriveStatusResponse(
        configured=status.configured,
        connected=status.connected,
        storage_type="google_drive",
        folder_name="Vercel Blob" if status.configured else None,
        master_filename=repository.master_filename,
        message=status.message,
    )
