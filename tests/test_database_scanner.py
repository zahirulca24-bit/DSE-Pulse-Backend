"""Prove database OHLC and scanner persistence are authoritative when available."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_database_only_rows_drive_scanner_and_persist_latest(
    database_client: TestClient,
    scanner_csv: bytes,
) -> None:
    imported = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("scanner.csv", scanner_csv, "text/csv")},
    ).json()
    assert imported["ok"] is True

    result = database_client.post("/scanner/run").json()
    assert result["ok"] is True
    assert result["mode"] == "database"
    assert result["data_source"] == "database"
    assert result["scanned_symbols"] == 4
    assert all(item["data_mode"] == "Database" for item in result["candidates"])

    latest = database_client.get("/scanner/latest").json()
    assert latest["ok"] is True
    assert latest["mode"] == "database"
    assert latest["data_source"] == "database"
    assert latest["scanned_symbols"] == 4
    assert all(item["data_mode"] == "Database" for item in latest["candidates"])

    signals = database_client.get("/signals").json()
    assert signals["mode"] == "database"
    assert signals["data_source"] == "database"
    assert all(item["signal_status"] in {"qualified", "watch"} for item in signals["signals"])

    status = database_client.get("/scanner/status").json()
    assert status["scanner_ready"] is True
    assert status["mode"] == "database"
    assert status["universe_source"] == "database"
    assert status["latest_scan_available"] is True


def test_database_takes_priority_over_local_cache(
    database_client: TestClient,
    scanner_csv: bytes,
) -> None:
    database_import = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("database.csv", scanner_csv, "text/csv")},
    ).json()
    assert database_import["ok"] is True

    cache_import = database_client.post(
        "/data/ohlc/import",
        files={"file": ("cache.csv", scanner_csv, "text/csv")},
    ).json()
    assert cache_import["ok"] is True

    result = database_client.post("/scanner/run").json()
    assert result["ok"] is True
    assert result["mode"] == "database"
    assert result["data_source"] == "database"
    assert result["scanned_symbols"] == 4
    assert all(item["data_mode"] == "Database" for item in result["candidates"])

    latest = database_client.get("/scanner/latest").json()
    assert latest["mode"] == "database"
    assert latest["data_source"] == "database"

    signals = database_client.get("/signals").json()
    assert signals["data_source"] == "database"

    status = database_client.get("/scanner/status").json()
    assert status["scanner_ready"] is True
    assert status["mode"] == "database"
    assert status["universe_source"] == "database"


def test_non_production_can_fallback_to_local_when_database_has_no_rows(
    database_client: TestClient,
    scanner_csv: bytes,
) -> None:
    cache_import = database_client.post(
        "/data/ohlc/import",
        files={"file": ("cache.csv", scanner_csv, "text/csv")},
    ).json()
    assert cache_import["ok"] is True

    result = database_client.post("/scanner/run").json()
    assert result["ok"] is True
    assert result["mode"] == "local_csv"
    assert result["data_source"] == "local_csv"

    latest = database_client.get("/scanner/latest").json()
    assert latest["mode"] == "local_csv"
    assert latest["data_source"] == "local_csv"


def test_production_never_falls_back_to_ephemeral_local_storage(
    database_client: TestClient,
    scanner_csv: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_import = database_client.post(
        "/data/ohlc/import",
        files={"file": ("cache.csv", scanner_csv, "text/csv")},
    ).json()
    assert cache_import["ok"] is True

    monkeypatch.setenv("APP_MODE", "production")
    get_settings.cache_clear()

    result = database_client.post("/scanner/run").json()
    assert result["ok"] is False
    assert result["mode"] == "no_data"
    assert result["data_source"] == "none"
    assert result["candidates"] == []

    latest = database_client.get("/scanner/latest").json()
    assert latest["ok"] is False
    assert latest["mode"] == "no_scan"
    assert latest["data_source"] == "none"

    status = database_client.get("/scanner/status").json()
    assert status["scanner_ready"] is False
    assert status["universe_source"] == "none"
