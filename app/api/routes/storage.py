"""Vercel Blob storage readiness route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.blob import BlobStatusResponse
from app.services.blob_ohlc_repository import BlobOhlcRepository
from app.services.dependencies import get_blob_ohlc_repository

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/status", response_model=BlobStatusResponse)
def get_storage_status(
    repository: Annotated[BlobOhlcRepository, Depends(get_blob_ohlc_repository)],
) -> BlobStatusResponse:
    status = repository.blob_status()
    return BlobStatusResponse(
        configured=status.configured,
        connected=status.connected,
        storage_type="vercel_blob",
        master_pathname=repository.master_pathname,
        message=status.message,
    )
