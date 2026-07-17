"""FastAPI service dependencies created from current settings."""

from app.core.config import get_settings
from app.services.csv_ingestion_service import CsvIngestionService
from app.services.ohlc_repository import OhlcRepository


def get_csv_ingestion_service() -> CsvIngestionService:
    """Return a stateless CSV ingestion service."""

    return CsvIngestionService()


def get_ohlc_repository() -> OhlcRepository:
    """Return a repository for the currently configured local storage path."""

    return OhlcRepository(get_settings().ohlc_storage_path)
