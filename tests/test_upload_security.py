"""Regression coverage for protected and bounded OHLC upload routes."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

_VALID_CSV = (
    b"symbol,trade_date,open,high,low,close,volume\n"
    b"ACI,2026-07-20,280,286,278,284,510000\n"
)


def test_data_import_rejects_missing_admin_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/data/ohlc/import",
            files={"file": ("ohlc.csv", _VALID_CSV, "text/csv")},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Data import authorization failed."}
    assert response.headers["cache-control"] == "no-store"


def test_data_import_rejects_wrong_admin_token() -> None:
    with TestClient(app, headers={"X-Data-Admin-Token": "wrong-token"}) as client:
        response = client.post(
            "/data/ohlc/import",
            files={"file": ("ohlc.csv", _VALID_CSV, "text/csv")},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Data import authorization failed."}


def test_data_import_fails_closed_when_token_is_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("DATA_ADMIN_TOKEN", raising=False)
    get_settings.cache_clear()

    try:
        with TestClient(app, headers={"X-Data-Admin-Token": "any-token"}) as client:
            response = client.post(
                "/data/ohlc/import",
                files={"file": ("ohlc.csv", _VALID_CSV, "text/csv")},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Data imports are disabled until DATA_ADMIN_TOKEN is configured."
    }


def test_data_import_rejects_payload_over_limit(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "64")
    get_settings.cache_clear()

    try:
        with TestClient(app, headers={"X-Data-Admin-Token": "test-data-admin-token"}) as client:
            response = client.post(
                "/data/ohlc/import",
                files={"file": ("ohlc.csv", _VALID_CSV, "text/csv")},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 413
    assert response.json() == {"detail": "Upload exceeds the configured 6.10352e-05 MB limit."}


def test_read_only_data_route_does_not_require_admin_token() -> None:
    with TestClient(app) as client:
        response = client.get("/data/status")

    assert response.status_code == 200
