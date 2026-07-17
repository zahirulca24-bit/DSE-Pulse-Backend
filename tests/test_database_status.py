"""Optional database status and startup safety tests."""

from fastapi.testclient import TestClient


def test_database_status_not_configured(client: TestClient) -> None:
    payload = client.get("/db/status").json()
    assert payload == {
        "configured": False,
        "connected": False,
        "database_type": "postgres",
        "message": "DATABASE_URL is not configured.",
    }


def test_database_status_never_exposes_url_or_password(database_client: TestClient) -> None:
    response = database_client.get("/db/status")
    text = response.text.lower()
    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert "sqlite" not in text
    assert "database_url" not in text
    assert "password" not in text


def test_app_and_health_start_without_database(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/status").json()["database_connected"] is False


def test_database_init_safe_error_when_not_configured(client: TestClient) -> None:
    payload = client.post("/db/init").json()
    assert payload["ok"] is False
    assert payload["message"] == "DATABASE_URL is not configured."


def test_database_init_is_idempotent(database_client: TestClient) -> None:
    first = database_client.post("/db/init").json()
    second = database_client.post("/db/init").json()
    assert first == {"ok": True, "message": "Database tables initialized."}
    assert second == first


def test_supabase_database_url_alias_is_accepted(
    client: TestClient,
    monkeypatch,
    tmp_path,
) -> None:
    from app.core.config import get_settings
    from app.db.init_db import initialize_database
    from app.services.dependencies import get_database_manager

    database_path = tmp_path / "alias.sqlite3"
    monkeypatch.setenv("SUPABASE_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    get_settings.cache_clear()
    get_database_manager.cache_clear()
    assert initialize_database(get_database_manager()) is True
    payload = client.get("/db/status").json()
    assert payload["configured"] is True
    assert payload["connected"] is True


def test_database_url_has_priority_over_alias(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings

    primary = tmp_path / "primary.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{primary}")
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "invalid://alias")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.selected_database_url.endswith("primary.sqlite3")
