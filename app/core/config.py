"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe local and optional database defaults."""

    app_name: str = "DSE Pulse Backend"
    app_version: str = "0.1.0"
    app_mode: str = "demo"
    frontend_origin: str = ""
    database_url: str = ""
    supabase_database_url: str = ""
    ohlc_storage_path: Path = Path("storage/dse_ohlc.csv")
    scanner_storage_path: Path = Path("storage/scanner_latest.json")

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
