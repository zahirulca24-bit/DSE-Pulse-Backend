"""Regression tests for centralized privileged-route authorization."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def raw_client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def _preview(client: TestClient, headers: dict[str, str] | None = None):
    payload = b"symbol,trade_date,open,high,low,close,volume\nACI,2026-07-20,10,11,9,10.5,1000\n"
    return client.post(
        "/data/ohlc/preview",
        headers=headers,
        files={"file": ("ohlc.csv", payload, "text/csv")},
    )


def test_privileged_route_is_disabled_without_configured_token(
    raw_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BACKEND_ADMIN_TOKEN", raising=False)
    get_settings.cache_clear()

    response = raw_client.post("/db/init")

    assert response.status_code == 503
    assert "BACKEND_ADMIN_TOKEN" in response.json()["detail"]


def test_privileged_route_rejects_invalid_token(
    raw_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "correct-secret")
    get_settings.cache_clear()

    response = raw_client.post("/scanner/run", headers={"X-Admin-Token": "wrong-secret"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Backend administrator authorization failed."


def test_admin_token_allows_protected_preview(
    raw_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "correct-secret")
    get_settings.cache_clear()

    response = _preview(raw_client, {"X-Admin-Token": "correct-secret"})

    assert response.status_code == 200
    assert response.json()["valid_rows"] == 1


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/db/init"),
        ("post", "/scanner/run"),
        ("post", "/data/ohlc/import"),
        ("post", "/data/ohlc/import-db"),
    ],
)
def test_protected_write_routes_reject_missing_header(
    raw_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "correct-secret")
    get_settings.cache_clear()
    kwargs = {}
    if path.startswith("/data/"):
        payload = b"symbol,trade_date,open,high,low,close,volume\nACI,2026-07-20,10,11,9,10.5,1000\n"
        kwargs["files"] = {"file": ("ohlc.csv", payload, "text/csv")}

    response = raw_client.request(method, path, **kwargs)

    assert response.status_code == 403
