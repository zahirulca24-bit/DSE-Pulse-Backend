"""FastAPI service dependencies created from current settings."""

from functools import lru_cache

from app.core.config import get_settings
from app.db.database import DatabaseManager
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.services.csv_ingestion_service import CsvIngestionService
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


def get_ohlc_repository() -> OhlcRepository:
    return OhlcRepository(get_settings().ohlc_storage_path)


def get_scanner_repository() -> ScannerRepository:
    return ScannerRepository(get_settings().scanner_storage_path)


def get_ohlc_db_repository() -> OhlcDbRepository:
    return OhlcDbRepository(get_database_manager())


def get_scanner_db_repository() -> ScannerDbRepository:
    return ScannerDbRepository(get_database_manager())


def get_scanner_engine() -> ScannerEngine:
    return ScannerEngine(IndicatorService())
