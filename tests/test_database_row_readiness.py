"""Regression tests for row-backed database market readiness."""

from fastapi.testclient import TestClient


def test_empty_database_tables_are_not_market_data(database_client: TestClient) -> None:
    payload = database_client.get("/data/source").json()

    assert payload["database_available"] is False
    assert payload["market_data_available"] is False
    assert payload["preferred_source"] == "none"
    assert payload["fallback_order"] == []


def test_database_becomes_ready_only_after_verified_rows(
    database_client: TestClient,
) -> None:
    csv_content = (
        b"symbol,trade_date,open,high,low,close,volume\n"
        b"GP,2026-07-30,280,286,278,284.5,510000\n"
    )
    imported = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("verified.csv", csv_content, "text/csv")},
    )

    assert imported.status_code == 200
    assert imported.json()["ok"] is True

    payload = database_client.get("/data/source").json()
    assert payload["database_available"] is True
    assert payload["market_data_available"] is True
    assert payload["preferred_source"] == "database"
    assert payload["fallback_order"] == ["database"]
