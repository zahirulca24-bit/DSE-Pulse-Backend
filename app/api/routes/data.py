"""Local CSV preview, import, and status routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas.data import DataImportResponse, DataPreviewResponse, DataStatusResponse
from app.services.csv_ingestion_service import NORMALIZED_HEADERS, CsvIngestionService
from app.services.dependencies import (
    get_csv_ingestion_service,
    get_ohlc_repository,
    get_scanner_repository,
)
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_repository import ScannerRepository

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/ohlc/preview", response_model=DataPreviewResponse)
async def preview_ohlc_csv(
    file: Annotated[UploadFile, File()],
    ingestion_service: Annotated[CsvIngestionService, Depends(get_csv_ingestion_service)],
) -> DataPreviewResponse:
    result = ingestion_service.parse_bytes(await file.read(), file.filename or "uploaded.csv")
    return DataPreviewResponse(
        ok=result.ok,
        mode="local_preview",
        filename=result.filename,
        detected_headers=result.detected_headers,
        normalized_headers=list(NORMALIZED_HEADERS),
        valid_rows=len(result.valid_rows),
        invalid_rows=result.invalid_rows,
        symbols_count=result.symbols_count,
        latest_trade_date=result.latest_trade_date,
        preview_rows=result.valid_rows[:20],
        warnings=result.warnings,
        errors=result.errors,
    )


@router.post("/ohlc/import", response_model=DataImportResponse)
async def import_ohlc_csv(
    file: Annotated[UploadFile, File()],
    ingestion_service: Annotated[CsvIngestionService, Depends(get_csv_ingestion_service)],
    repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    scanner_repository: Annotated[
        ScannerRepository,
        Depends(get_scanner_repository),
    ],
) -> DataImportResponse:
    result = ingestion_service.parse_bytes(await file.read(), file.filename or "uploaded.csv")
    if not result.ok:
        return DataImportResponse(
            ok=False,
            mode="local_csv",
            stored_path=repository.stored_path,
            valid_rows=len(result.valid_rows),
            invalid_rows=result.invalid_rows,
            symbols_count=result.symbols_count,
            latest_trade_date=result.latest_trade_date,
            message="DSE OHLC CSV was not imported.",
            warnings=result.warnings,
            errors=result.errors,
        )
    repository.save(result)
    scanner_repository.clear()
    return DataImportResponse(
        ok=True,
        mode="local_csv",
        stored_path=repository.stored_path,
        valid_rows=len(result.valid_rows),
        invalid_rows=result.invalid_rows,
        symbols_count=result.symbols_count,
        latest_trade_date=result.latest_trade_date,
        message="DSE OHLC CSV imported into local storage.",
        warnings=result.warnings,
        errors=result.errors,
    )


@router.get("/status", response_model=DataStatusResponse)
def get_data_status(repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)]) -> DataStatusResponse:
    return repository.get_status()
