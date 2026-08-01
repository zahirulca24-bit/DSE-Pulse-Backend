"""Environment-backed application configuration."""

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PRODUCTION_MODES = {"production", "prod"}


class Settings(BaseSettings):
    """Runtime settings with safe local and optional database defaults."""

    app_name: str = "DSE Pulse Backend"
    app_version: str = "0.1.0"
    app_mode: str = "demo"
    frontend_origin: str = ""
    database_url: str = ""
    supabase_database_url: str = ""
    backend_admin_token: str = ""
    collector_admin_token: str = ""
    dse_collector_source: str = ""
    ohlc_storage_path: Path = Path("storage/dse_ohlc.csv")
    scanner_storage_path: Path = Path("storage/scanner_latest.json")
    scanner_scheduler_state_path: Path = Path("storage/scanner_scheduler_state.json")
    collector_storage_path: Path = Path("storage/collector_jobs.json")
    scanner_scheduler_enabled: bool = False
    dse_market_holidays: str = ""
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
    def is_production(self) -> bool:
        """Return whether the application is running in production mode."""

        return self.app_mode.strip().lower() in _PRODUCTION_MODES

    @property
    def in_process_scheduler_enabled(self) -> bool:
        """Allow the local scheduler only outside production Cloud Run workloads."""

        return self.scanner_scheduler_enabled and not self.is_production

    @property
    def selected_database_url(self) -> str:
        """Select DATABASE_URL before the optional Supabase alias."""

        return self.database_url.strip() or self.supabase_database_url.strip()

    @property
    def google_drive_configured(self) -> bool:
        """Return whether legacy Google Drive compatibility is configured."""

        credentials = (
            self.google_drive_service_account_json.strip()
            or self.google_drive_service_account_json_b64.strip()
        )
        return bool(self.google_drive_folder_id.strip() and credentials)

    @property
    def dse_market_holiday_dates(self) -> set[date]:
        """Parse optional comma-separated YYYY-MM-DD exchange holidays fail-closed."""

        holidays: set[date] = set()
        for value in self.dse_market_holidays.split(","):
            item = value.strip()
            if not item:
                continue
            try:
                holidays.add(date.fromisoformat(item))
            except ValueError:
                continue
        return holidays

    @property
    def cors_origins(self) -> list[str]:
        """Return explicit browser origins with no development leakage in production."""

        production_origin = self.frontend_origin.strip().rstrip("/")
        if self.is_production:
            return [production_origin] if production_origin else []

        origins = ["http://localhost:3000", "http://localhost:5173"]
        if production_origin and production_origin not in origins:
            origins.append(production_origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
