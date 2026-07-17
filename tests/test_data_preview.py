"""CSV preview endpoint tests."""

from fastapi.testclient import TestClient


def test_preview_accepts_valid_csv_and_does_not_save(client: TestClient) -> None:
    content = (
        b"symbol,trade_date,open,high,low,close,volume\n"
        b"gp,2026-06-11,280,286,278,284.5,510000\n"
    )

    response = client.post(
        "/data/ohlc/preview",
        files={"file": ("dse_ohlc.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["mode"] == "local_preview"
    assert payload["valid_rows"] == 1
    assert payload["invalid_rows"] == 0
    assert payload["symbols_count"] == 1
    assert payload["latest_trade_date"] == "2026-06-11"
    assert payload["preview_rows"][0]["symbol"] == "GP"
    assert payload["preview_rows"][0]["trade"] is None
    assert payload["preview_rows"][0]["value"] is None
    assert client.get("/data/status").json()["data_available"] is False


def test_preview_rejects_missing_required_headers(client: TestClient) -> None:
    content = b"symbol,date,close\nGP,2026-06-11,284.5\n"

    response = client.post(
        "/data/ohlc/preview",
        files={"file": ("bad.csv", content, "text/csv")},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["valid_rows"] == 0
    assert any("Missing required columns" in error for error in payload["errors"])


def test_preview_counts_invalid_rows_and_keeps_valid_rows(client: TestClient) -> None:
    content = (
        b"symbol,date,open,high,low,close,volume\n"
        b"GP,2026-06-11,280,286,278,284.5,510000\n"
        b"BAD,11-06-2026,10,12,9,11,100\n"
        b"LOWHIGH,2026-06-11,10,8,9,10,100\n"
    )

    payload = client.post(
        "/data/ohlc/preview",
        files={"file": ("mixed.csv", content, "text/csv")},
    ).json()

    assert payload["ok"] is True
    assert payload["valid_rows"] == 1
    assert payload["invalid_rows"] == 2
    assert len(payload["errors"]) == 2
