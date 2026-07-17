"""CSV import and local data status tests."""

import csv
from pathlib import Path

from fastapi.testclient import TestClient


def _fixture_bytes() -> bytes:
    return Path("tests/fixtures/sample_dse_ohlc.csv").read_bytes()


def test_import_saves_normalized_valid_csv(
    client: TestClient,
    isolated_storage: Path,
) -> None:
    response = client.post(
        "/data/ohlc/import",
        files={"file": ("sample.csv", _fixture_bytes(), "text/csv")},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["valid_rows"] == 4
    assert payload["invalid_rows"] == 0
    assert payload["symbols_count"] == 3
    assert isolated_storage.exists()

    with isolated_storage.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == [
        "symbol",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade",
        "value",
    ]
    assert rows[0]["symbol"] == "GP"
    assert rows[0]["trade_date"] == "2026-06-10"


def test_import_does_not_overwrite_when_no_valid_rows(
    client: TestClient,
    isolated_storage: Path,
) -> None:
    first = client.post(
        "/data/ohlc/import",
        files={"file": ("sample.csv", _fixture_bytes(), "text/csv")},
    )
    assert first.json()["ok"] is True
    original = isolated_storage.read_bytes()

    invalid = (
        b"symbol,date,open,high,low,close,volume\n"
        b",not-a-date,-1,0,2,x,1.5\n"
    )
    second = client.post(
        "/data/ohlc/import",
        files={"file": ("invalid.csv", invalid, "text/csv")},
    )

    assert second.json()["ok"] is False
    assert isolated_storage.read_bytes() == original


def test_data_status_false_without_import(client: TestClient) -> None:
    payload = client.get("/data/status").json()

    assert payload == {
        "data_available": False,
        "data_source": "none",
        "stored_path": None,
        "symbols_count": None,
        "rows_count": None,
        "latest_trade_date": None,
        "earliest_trade_date": None,
        "message": "No local DSE OHLC CSV has been imported yet.",
    }


def test_data_status_reports_real_counts_after_import(client: TestClient) -> None:
    imported = client.post(
        "/data/ohlc/import",
        files={"file": ("sample.csv", _fixture_bytes(), "text/csv")},
    )
    assert imported.json()["ok"] is True

    payload = client.get("/data/status").json()
    assert payload["data_available"] is True
    assert payload["data_source"] == "local_csv"
    assert payload["symbols_count"] == 3
    assert payload["rows_count"] == 4
    assert payload["latest_trade_date"] == "2026-06-11"
    assert payload["earliest_trade_date"] == "2026-06-09"
