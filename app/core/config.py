"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe local, Google Drive, and optional database defaults."""

    app_name: str = "DSE Pulse Backend"
    app_version: str = "0.1.0"
    app_mode: str = "demo"
    frontend_origin: str = ""
    database_url: str = ""
    supabase_database_url: str = ""
    collector_admin_token: str = ""
    ohlc_storage_path: Path = Path("storage/dse_ohlc.csv")
    scanner_storage_path: Path = Path("storage/scanner_latest.json")
    collector_storage_path: Path = Path("storage/collector_jobs.json")
    google_drive_folder_id: str = ""
    google_drive_master_filename: str = "DSE_OHLC_MASTER.csv"
    google_drive_service_account_json: str = ""
    google_drive_service_account_json_b64: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def selected_database_url(self) -> str:
        """Select DATABASE_URL before the optional Supabase alias."""

        return self.database_url.strip() or self.supabase_database_url.strip()

    @property
    def google_drive_configured(self) -> bool:
        """Return whether unattended Google Drive storage has the required configuration."""

        credentials = (
            self.google_drive_service_account_json.strip()
            or self.google_drive_service_account_json_b64.strip()
        )
        return bool(self.google_drive_folder_id.strip() and credentials)

    @property
    def cors_origins(self) -> list[str]:
        """Return explicit allowed frontend origins without wildcard access."""

        origins = ["http://localhost:3000", "http://localhost:5173"]
        production_origin = self.frontend_origin.strip().rstrip("/")
        if production_origin and production_origin not in origins:
            origins.append(production_origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
