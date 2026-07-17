"""FastAPI service dependencies created from current settings."""

from functools import lru_cache

from app.core.config import get_settings
from app.db.database import DatabaseManager
from app.repositories.collector_repository import CollectorRepository
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.services.collector_service import CollectorService
from app.services.collector_source import BdshareCollectorSource, CollectorSource
from app.services.csv_ingestion_service import CsvIngestionService
from app.services.data_audit_service import DataAuditService
from app.services.indicator_service import IndicatorService
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository


@lru_cache
def get_database_manager() -> DatabaseManager:
    """Return one lazy database manager for current environment settings."""

    return DatabaseManager(get_settings().selected_database_url)


def get_csv_ingestion_service() -> CsvIngestionService:
    return CsvIngestionService()


def get_data_audit_service() -> DataAuditService:
    return DataAuditService(get_database_manager())


def get_ohlc_repository() -> OhlcRepository:
    return OhlcRepository(get_settings().ohlc_storage_path)


def get_scanner_repository() -> ScannerRepository:
    return ScannerRepository(get_settings().scanner_storage_path)


def get_ohlc_db_repository() -> OhlcDbRepository:
    return OhlcDbRepository(get_database_manager())


def get_scanner_db_repository() -> ScannerDbRepository:
    return ScannerDbRepository(get_database_manager())


def get_collector_repository() -> CollectorRepository:
    return CollectorRepository(get_database_manager())


def get_collector_source() -> CollectorSource:
    return BdshareCollectorSource()


def get_collector_service() -> CollectorService:
    return CollectorService(
        settings=get_settings(),
        repository=get_collector_repository(),
        ohlc_repository=get_ohlc_db_repository(),
        audit_service=get_data_audit_service(),
        source=get_collector_source(),
    )


def get_scanner_engine() -> ScannerEngine:
    return ScannerEngine(IndicatorService())
