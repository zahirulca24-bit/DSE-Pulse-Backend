"""Prove legacy database storage cannot become the production scanner source."""

from fastapi.testclient import TestClient


def test_database_only_rows_are_ignored_by_scanner(
    database_client: TestClient,
    scanner_csv: bytes,
) -> None:
    imported = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("scanner.csv", scanner_csv, "text/csv")},
    ).json()
    assert imported["ok"] is True

    result = database_client.post("/scanner/run").json()
    assert result["ok"] is False
    assert result["mode"] == "no_data"
    assert result["data_source"] == "none"
    assert result["candidates"] == []

    latest = database_client.get("/scanner/latest").json()
    assert latest["ok"] is False
    assert latest["mode"] == "no_scan"
    assert latest["data_source"] == "none"

    signals = database_client.get("/signals").json()
    assert signals["mode"] == "no_scan"
    assert signals["data_source"] == "none"
    assert signals["signals"] == []

    status = database_client.get("/scanner/status").json()
    assert status["scanner_ready"] is False
    assert status["universe_source"] == "none"


def test_scanner_uses_approved_local_cache_even_when_database_is_available(
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
    assert result["mode"] == "local_csv"
    assert result["data_source"] == "local_csv"
    assert result["scanned_symbols"] == 4
    assert all(item["data_mode"] == "Local CSV" for item in result["candidates"])

    latest = database_client.get("/scanner/latest").json()
    assert latest["data_source"] == "local_csv"
    assert latest["scanned_symbols"] == 4

    signals = database_client.get("/signals").json()
    assert signals["data_source"] == "local_csv"
    assert all(item["signal_status"] in {"qualified", "watch"} for item in signals["signals"])

    status = database_client.get("/scanner/status").json()
    assert status["scanner_ready"] is True
    assert status["mode"] == "local_csv"
    assert status["universe_source"] == "local_csv"
