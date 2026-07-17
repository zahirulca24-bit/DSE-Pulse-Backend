"""Fallback behavior when optional database configuration is absent."""

from fastapi.testclient import TestClient


def test_import_db_returns_safe_error_without_configuration(client: TestClient) -> None:
    response = client.post(
        "/data/ohlc/import-db",
        files={"file": ("sample.csv", b"symbol,trade_date,open,high,low,close,volume\n", "text/csv")},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["message"] == "DATABASE_URL is not configured."
    assert "url" not in response.text.lower().replace("database_url", "")


def test_symbols_and_status_fall_back_to_local(imported_client: TestClient) -> None:
    assert imported_client.get("/status").json()["data_source"] == "local_csv"
    assert imported_client.get("/symbols").json()["data_source"] == "local_csv"


def test_ohlc_explicit_local_source(imported_client: TestClient) -> None:
    payload = imported_client.get("/ohlc/gp", params={"source": "local_csv", "limit": 2}).json()
    assert payload["data_source"] == "local_csv"
    assert payload["rows_count"] == 2


def test_ohlc_explicit_database_returns_safe_error(client: TestClient) -> None:
    response = client.get("/ohlc/GP", params={"source": "database"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Database OHLC storage is unavailable."


def test_scanner_falls_back_to_local_csv(imported_client: TestClient) -> None:
    payload = imported_client.post("/scanner/run").json()
    assert payload["ok"] is True
    assert payload["data_source"] == "local_csv"
