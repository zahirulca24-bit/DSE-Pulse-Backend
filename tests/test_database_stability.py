"""Regression tests for database transaction and initialization stability."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.routes import database as database_routes
from app.db.database import DatabaseManager
from app.main import app
from app.services.dependencies import get_database_manager


def test_database_session_rolls_back_before_close(tmp_path: Path) -> None:
    database_path = tmp_path / "rollback.sqlite3"
    manager = DatabaseManager(f"sqlite+pysqlite:///{database_path}")

    with manager.session() as session:
        session.execute(text("CREATE TABLE entries (value INTEGER NOT NULL)"))
        session.commit()

    with pytest.raises(RuntimeError, match="force rollback"):
        with manager.session() as session:
            session.execute(text("INSERT INTO entries (value) VALUES (1)"))
            raise RuntimeError("force rollback")

    with manager.session() as session:
        count = session.execute(text("SELECT COUNT(*) FROM entries")).scalar_one()

    assert count == 0
    manager.dispose()


def test_db_init_returns_503_when_database_is_not_configured(
    client: TestClient,
) -> None:
    response = client.post("/db/init")

    assert response.status_code == 503
    assert response.json() == {"detail": "DATABASE_URL is not configured."}


def test_db_init_returns_503_when_table_creation_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "init-failure.sqlite3"
    manager = DatabaseManager(f"sqlite+pysqlite:///{database_path}")
    app.dependency_overrides[get_database_manager] = lambda: manager
    monkeypatch.setattr(database_routes, "initialize_database", lambda _: False)

    try:
        response = client.post("/db/init")
    finally:
        app.dependency_overrides.pop(get_database_manager, None)
        manager.dispose()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database tables could not be initialized."
    }
