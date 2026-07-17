"""Backend and scanner status endpoint tests."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_status_is_demo_and_broker_is_disconnected(client: TestClient) -> None:
    response = client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["data_source"] == "demo"
    assert payload["broker_connected"] is False
    assert payload["database_connected"] is False
    assert payload["live_market_connected"] is False
    assert payload["symbols_count"] is None
    assert payload["rows_count"] is None


def test_status_uses_real_local_csv_counts(
    client: TestClient,
    isolated_storage: Path,
) -> None:
    content = Path("tests/fixtures/sample_dse_ohlc.csv").read_bytes()
    imported = client.post(
        "/data/ohlc/import",
        files={"file": ("sample.csv", content, "text/csv")},
    )
    assert imported.json()["ok"] is True
    assert isolated_storage.exists()

    response = client.get("/status")
    payload = response.json()
    assert payload["data_source"] == "local_csv"
    assert payload["database_connected"] is False
    assert payload["live_market_connected"] is False
    assert payload["broker_connected"] is False
    assert payload["last_data_date"] == "2026-06-11"
    assert payload["symbols_count"] == 3
    assert payload["rows_count"] == 4


def test_scanner_status_has_execution_disabled(client: TestClient) -> None:
    response = client.get("/scanner/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scanner_ready"] is False
    assert payload["mode"] == "no_data"
    assert payload["data_available"] is False
    assert payload["latest_scan_available"] is False
    assert payload["execution_enabled"] is False
    assert payload["last_scan_at"] is None
