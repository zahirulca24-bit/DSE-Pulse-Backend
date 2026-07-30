"""Regression tests for production runtime safety settings."""

from app.core.config import Settings


def test_development_cors_keeps_local_origins() -> None:
    settings = Settings(
        app_mode="development",
        frontend_origin="https://frontend.example.com/",
    )

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://frontend.example.com",
    ]


def test_production_cors_allows_only_configured_frontend() -> None:
    settings = Settings(
        app_mode="production",
        frontend_origin="https://frontend.example.com/",
    )

    assert settings.cors_origins == ["https://frontend.example.com"]


def test_production_without_frontend_origin_fails_closed() -> None:
    settings = Settings(app_mode="production", frontend_origin="")

    assert settings.cors_origins == []


def test_in_process_scheduler_is_never_enabled_in_production() -> None:
    production = Settings(
        app_mode="prod",
        scanner_scheduler_enabled=True,
    )
    development = Settings(
        app_mode="development",
        scanner_scheduler_enabled=True,
    )

    assert production.in_process_scheduler_enabled is False
    assert development.in_process_scheduler_enabled is True
