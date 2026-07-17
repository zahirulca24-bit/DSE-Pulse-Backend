"""Database OHLC audit endpoint tests."""

from fastapi.testclient import TestClient

from tests.conftest import build_symbol_rows, csv_bytes


def test_data_audit_is_safe_without_database(client: TestClient) -> None:
    response = client.get("/data/audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["data_source"] == "none"
    assert payload["scanner_ready"] is False
    assert payload["rows_count"] == 0


def test_data_audit_reports_history_and_latest_date_coverage(database_client: TestClient) -> None:
    rows = build_symbol_rows("FULLHISTORY", days=65)
    rows += build_symbol_rows("SHORTHISTORY", days=30)

    imported = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("audit.csv", csv_bytes(rows), "text/csv")},
    )
    assert imported.status_code == 200
    assert imported.json()["ok"] is True

    response = database_client.get("/data/audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data_source"] == "database"
    assert payload["rows_count"] == 95
    assert payload["symbols_count"] == 2
    assert payload["duplicate_symbol_date_rows"] == 0
    assert payload["zero_volume_rows"] == 0
    assert payload["non_positive_price_rows"] == 0
    assert payload["invalid_ohlc_rows"] == 0
    assert payload["symbols_with_fewer_than_60_rows"] == 1
    assert payload["latest_date_symbols_count"] == 1
    assert payload["latest_date_coverage_percent"] == 50.0
    assert payload["stale_symbols_count"] == 1
    assert payload["scanner_ready"] is True
