"""Protected production collector endpoint tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def raw_client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_collector_run_uses_backend_admin_and_requires_database_tables(
    client: TestClient,
) -> None:
    response = client.post("/collector/run", json={"trade_date": "2026-07-01"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Database tables are unavailable. Run POST /db/init first."


def test_collector_run_does_not_accept_legacy_collector_token(
    client: TestClient,
) -> None:
    response = client.post(
        "/collector/run",
        json={"trade_date": "2026-07-01"},
        headers={"X-Collector-Token": "legacy-token"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Database tables are unavailable. Run POST /db/init first."


def test_collector_run_rejects_missing_backend_admin_token(
    raw_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "server-secret")

    response = raw_client.post("/collector/run", json={"trade_date": "2026-07-01"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Backend administrator authorization failed."
