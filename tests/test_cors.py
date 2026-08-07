from app.core.config import Settings
from app.core.cors import normalize_origins


def test_normalize_origins_deduplicates_and_strips_trailing_slashes() -> None:
    assert normalize_origins(
        "https://frontend-a.example/",
        "https://frontend-b.example, https://frontend-a.example",
    ) == [
        "https://frontend-a.example",
        "https://frontend-b.example",
    ]


def test_production_cors_allows_primary_and_extra_origins() -> None:
    settings = Settings(
        app_mode="production",
        frontend_origin="https://frontend-hash.run.app",
        cors_origins_extra="https://frontend-canonical.run.app",
    )

    assert settings.cors_origins == [
        "https://frontend-hash.run.app",
        "https://frontend-canonical.run.app",
    ]
