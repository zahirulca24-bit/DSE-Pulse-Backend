"""FastAPI service dependencies created from current settings."""

import os
from functools import lru_cache

from app.core.config import get_settings
from app.db.database import DatabaseManager
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.services.blob_ohlc_repository import BlobOhlcRepository
from app.services.collector_job_repository import CollectorJobRepository
from app.services.collector_service import CollectorService
from app.services.collector_source import BdshareCollectorSource, CollectorSource
from app.services.csv_ingestion_service import CsvIngestionService
from app.services.data_audit_service import DataAuditService
from app.services.drive_ohlc_repository import DriveOhlcRepository
from app.services.google_drive_client import GoogleDriveClient
from app.services.indicator_service import IndicatorService
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository
from app.services.scanner_scheduler import MarketScannerScheduler
from app.services.scanner_scheduler_state import ScannerSchedulerStateRepository
from app.services.scanner_service import ScannerService
from app.services.vercel_blob_client import VercelBlobClient


@lru_cache
def get_database_manager() -> DatabaseManager:
    """Return one lazy database manager for current environment settings."""

    return DatabaseManager(get_settings().selected_database_url)


@lru_cache
def get_vercel_blob_client() -> VercelBlobClient:
    """Return one Vercel Blob client using the backend runtime token."""

    return VercelBlobClient(token=os.getenv("BLOB_READ_WRITE_TOKEN", ""))


@lru_cache
def get_google_drive_client() -> GoogleDriveClient:
    """Legacy compatibility client; Google Drive is not the production storage path."""

    settings = get_settings()
    return GoogleDriveClient(
        folder_id=settings.google_drive_folder_id,
        service_account_json=settings.google_drive_service_account_json,
        service_account_json_b64=settings.google_drive_service_account_json_b64,
    )


def get_csv_ingestion_service() -> CsvIngestionService:
    return CsvIngestionService()


def get_data_audit_service() -> DataAuditService:
    return DataAuditService(get_database_manager())


def get_local_ohlc_repository() -> OhlcRepository:
    return OhlcRepository(get_settings().ohlc_storage_path)


def get_blob_ohlc_repository() -> BlobOhlcRepository:
    return BlobOhlcRepository(
        local_repository=get_local_ohlc_repository(),
        blob_client=get_vercel_blob_client(),
        master_pathname=os.getenv("VERCEL_BLOB_MASTER_PATHNAME", "dse/DSE_OHLC_MASTER.csv"),
    )


def get_drive_ohlc_repository() -> DriveOhlcRepository:
    """Legacy compatibility repository; not used by the production app pipeline."""

    settings = get_settings()
    return DriveOhlcRepository(
        local_repository=get_local_ohlc_repository(),
        drive_client=get_google_drive_client(),
        master_filename=settings.google_drive_master_filename,
    )


def get_ohlc_repository() -> OhlcRepository:
    """Use Vercel Blob-backed local cache when configured, otherwise local CSV."""

    if get_vercel_blob_client().configured:
        return get_blob_ohlc_repository()
    return get_local_ohlc_repository()


def get_scanner_repository() -> ScannerRepository:
    return ScannerRepository(get_settings().scanner_storage_path)


def get_ohlc_db_repository() -> OhlcDbRepository:
    return OhlcDbRepository(get_database_manager())


def get_scanner_db_repository() -> ScannerDbRepository:
    return ScannerDbRepository(get_database_manager())


def get_collector_repository() -> CollectorJobRepository:
    """Return DB-free collector job-state persistence."""

    return CollectorJobRepository(get_settings().collector_storage_path)


def get_collector_source() -> CollectorSource:
    return BdshareCollectorSource()


def get_collector_service() -> CollectorService:
    """Build the production collector on Vercel Blob canonical OHLC storage."""

    return CollectorService(
        settings=get_settings(),
        repository=get_collector_repository(),
        ohlc_repository=get_blob_ohlc_repository(),
        source=get_collector_source(),
    )


def get_scanner_engine() -> ScannerEngine:
    return ScannerEngine(IndicatorService())


def get_scanner_service() -> ScannerService:
    """Build the single scanner execution path used by manual and scheduled scans."""

    return ScannerService(
        get_ohlc_repository(),
        get_scanner_repository(),
        get_scanner_engine(),
    )


@lru_cache
def get_market_scanner_scheduler() -> MarketScannerScheduler:
    """Return the process-wide market scheduler and persistent slot state."""

    settings = get_settings()
    return MarketScannerScheduler(
        settings=settings,
        scanner_service=get_scanner_service(),
        state_repository=ScannerSchedulerStateRepository(settings.scanner_scheduler_state_path),
    )
