"""FastAPI service dependencies created from current settings."""

from functools import lru_cache

from app.core.config import get_settings
from app.db.database import DatabaseManager
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
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


@lru_cache
def get_database_manager() -> DatabaseManager:
    """Return one lazy database manager for current environment settings."""

    return DatabaseManager(get_settings().selected_database_url)


@lru_cache
def get_google_drive_client() -> GoogleDriveClient:
    """Return one lazy Google Drive client for the configured storage folder."""

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


def get_drive_ohlc_repository() -> DriveOhlcRepository:
    settings = get_settings()
    return DriveOhlcRepository(
        local_repository=get_local_ohlc_repository(),
        drive_client=get_google_drive_client(),
        master_filename=settings.google_drive_master_filename,
    )


def get_ohlc_repository() -> OhlcRepository:
    """Use Drive-backed local cache when configured, otherwise preserve local CSV behavior."""

    if get_settings().google_drive_configured:
        return get_drive_ohlc_repository()
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
    """Build the production collector on Google Drive canonical OHLC storage."""

    return CollectorService(
        settings=get_settings(),
        repository=get_collector_repository(),
        ohlc_repository=get_drive_ohlc_repository(),
        source=get_collector_source(),
    )


def get_scanner_engine() -> ScannerEngine:
    return ScannerEngine(IndicatorService())
