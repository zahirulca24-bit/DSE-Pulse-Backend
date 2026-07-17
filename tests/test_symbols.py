"""Stored symbols endpoint tests."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_symbols_empty_without_local_data(client: TestClient) -> None:
    assert client.get("/symbols").json() == {
        "data_source": "none",
        "symbols_count": 0,
        "symbols": [],
    }


def test_symbols_are_alphabetically_sorted(client: TestClient) -> None:
    imported = client.post(
        "/data/ohlc/import",
        files={
            "file": (
                "sample.csv",
                Path("tests/fixtures/sample_dse_ohlc.csv").read_bytes(),
                "text/csv",
            )
        },
    )
    assert imported.json()["ok"] is True

    payload = client.get("/symbols").json()
    assert payload["data_source"] == "local_csv"
    assert payload["symbols_count"] == 3
    assert payload["symbols"] == ["BATBC", "GP", "SQURPHARMA"]
