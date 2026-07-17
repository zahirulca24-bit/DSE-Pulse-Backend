"""Backend and scanner status endpoint tests."""

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


def test_scanner_status_has_execution_disabled(client: TestClient) -> None:
    response = client.get("/scanner/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scanner_ready"] is True
    assert payload["execution_enabled"] is False
    assert payload["last_scan_at"] is None
