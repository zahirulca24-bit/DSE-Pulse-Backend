"""Database-priority scanner and signals tests."""

from fastapi.testclient import TestClient


def test_scanner_reads_and_persists_database_results(
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
    assert all(item["data_mode"] == "Database" for item in result["candidates"])

    latest = database_client.get("/scanner/latest").json()
    assert latest["data_source"] == "database"
    assert latest["scanned_symbols"] == 4

    signals = database_client.get("/signals").json()
    assert signals["data_source"] == "database"
    assert all(item["signal_status"] in {"qualified", "watch"} for item in signals["signals"])
