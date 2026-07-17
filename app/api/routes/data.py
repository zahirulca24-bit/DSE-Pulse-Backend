"""CSV preview/import and active data source routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.db.database import DatabaseManager
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.data import DataImportResponse, DataPreviewResponse, DataStatusResponse
from app.schemas.database import DatabaseImportResponse, DataSourceResponse
from app.services.csv_ingestion_service import NORMALIZED_HEADERS, CsvIngestionService
from app.services.dependencies import (
    get_csv_ingestion_service,
    get_database_manager,
    get_ohlc_db_repository,
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
    scanner_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
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


@router.post("/ohlc/import-db", response_model=DatabaseImportResponse)
async def import_ohlc_database(
    file: Annotated[UploadFile, File()],
    ingestion_service: Annotated[CsvIngestionService, Depends(get_csv_ingestion_service)],
    database_manager: Annotated[DatabaseManager, Depends(get_database_manager)],
    database_repository: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
) -> DatabaseImportResponse:
    """Validate and upsert normalized rows when database tables are ready."""

    connection = database_manager.get_status()
    if not connection.configured:
        return _database_import_error("DATABASE_URL is not configured.")
    if not connection.connected:
        return _database_import_error("Database connection is unavailable.")
    if not database_repository.is_available():
        return _database_import_error("Database tables are unavailable. Run POST /db/init first.")
    result = ingestion_service.parse_bytes(await file.read(), file.filename or "uploaded.csv")
    if not result.ok:
        return DatabaseImportResponse(
            ok=False,
            data_source="database",
            inserted_rows=0,
            updated_rows=0,
            invalid_rows=result.invalid_rows,
            symbols_count=result.symbols_count,
            latest_trade_date=result.latest_trade_date,
            message="DSE OHLC CSV was not imported into database.",
        )
    inserted, updated = database_repository.upsert(result.valid_rows)
    if inserted + updated == 0:
        return _database_import_error("Database import could not be completed safely.")
    return DatabaseImportResponse(
        ok=True,
        data_source="database",
        inserted_rows=inserted,
        updated_rows=updated,
        invalid_rows=result.invalid_rows,
        symbols_count=result.symbols_count,
        latest_trade_date=result.latest_trade_date,
        message="DSE OHLC CSV imported into database.",
    )


@router.get("/status", response_model=DataStatusResponse)
def get_data_status(repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)]) -> DataStatusResponse:
    """Preserve the original local-storage status endpoint contract."""

    return repository.get_status()


@router.get("/source", response_model=DataSourceResponse)
def get_data_source(
    database_repository: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    local_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
) -> DataSourceResponse:
    database_available = database_repository.is_available()
    local_available = local_repository.get_status().data_available
    if database_available:
        preferred = "database"
        fallback = ["database", "local_csv", "demo"]
    elif local_available:
        preferred = "local_csv"
        fallback = ["local_csv", "demo"]
    else:
        preferred = "demo"
        fallback = ["demo"]
    return DataSourceResponse(
        preferred_source=preferred,
        database_available=database_available,
        local_csv_available=local_available,
        fallback_order=fallback,
    )


def _database_import_error(message: str) -> DatabaseImportResponse:
    return DatabaseImportResponse(
        ok=False,
        data_source="database",
        inserted_rows=0,
        updated_rows=0,
        invalid_rows=0,
        symbols_count=0,
        latest_trade_date=None,
        message=message,
    )
