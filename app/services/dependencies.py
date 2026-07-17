"""FastAPI service dependencies created from current settings."""

from app.core.config import get_settings
from app.services.csv_ingestion_service import CsvIngestionService
from app.services.indicator_service import IndicatorService
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository


def get_csv_ingestion_service() -> CsvIngestionService:
    return CsvIngestionService()


def get_ohlc_repository() -> OhlcRepository:
    return OhlcRepository(get_settings().ohlc_storage_path)


def get_scanner_repository() -> ScannerRepository:
    return ScannerRepository(get_settings().scanner_storage_path)


def get_scanner_engine() -> ScannerEngine:
    return ScannerEngine(IndicatorService())
