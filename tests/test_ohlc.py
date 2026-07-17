"""Stored symbol OHLC endpoint tests."""

from pathlib import Path

from fastapi.testclient import TestClient


def _import_fixture(client: TestClient) -> None:
    response = client.post(
        "/data/ohlc/import",
        files={
            "file": (
                "sample.csv",
                Path("tests/fixtures/sample_dse_ohlc.csv").read_bytes(),
                "text/csv",
            )
        },
    )
    assert response.json()["ok"] is True


def test_ohlc_returns_rows_for_case_insensitive_symbol(client: TestClient) -> None:
    _import_fixture(client)

    payload = client.get("/ohlc/gp").json()
    assert payload["symbol"] == "GP"
    assert payload["data_source"] == "local_csv"
    assert payload["rows_count"] == 2
    assert [row["trade_date"] for row in payload["rows"]] == [
        "2026-06-11",
        "2026-06-10",
    ]


def test_ohlc_respects_limit_and_date_filters(client: TestClient) -> None:
    _import_fixture(client)

    limited = client.get("/ohlc/GP?limit=1").json()
    assert limited["rows_count"] == 1
    assert limited["rows"][0]["trade_date"] == "2026-06-11"

    filtered = client.get(
        "/ohlc/GP?start_date=2026-06-10&end_date=2026-06-10"
    ).json()
    assert filtered["rows_count"] == 1
    assert filtered["rows"][0]["trade_date"] == "2026-06-10"


def test_ohlc_returns_empty_rows_for_unknown_symbol(client: TestClient) -> None:
    _import_fixture(client)

    payload = client.get("/ohlc/UNKNOWN").json()
    assert payload == {
        "symbol": "UNKNOWN",
        "data_source": "local_csv",
        "rows_count": 0,
        "rows": [],
    }
