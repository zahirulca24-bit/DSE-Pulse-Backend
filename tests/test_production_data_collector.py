"""Production data import and collector contract tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def raw_client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_data_import_requires_admin_token(raw_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "correct-secret")
    response = raw_client.post(
        "/data/import",
        files={
            "file": (
                "ohlc.csv",
                b"symbol,trade_date,open,high,low,close,volume\nACI,2026-07-20,10,11,9,10.5,1000\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 403


def test_data_import_upserts_and_counts_duplicates(database_client: TestClient) -> None:
    first = database_client.post(
        "/data/import",
        files={
            "file": (
                "first.csv",
                (
                    b"symbol,trade_date,open,high,low,close,volume\n"
                    b"GP,2026-06-10,280,286,278,284.5,510000\n"
                    b"GP,2026-06-10,281,286,278,284.5,510000\n"
                    b"BATBC,2026-06-11,420,425,418,423,100000\n"
                ),
                "text/csv",
            )
        },
    ).json()

    assert first["ok"] is True
    assert first["inserted"] == 2
    assert first["updated"] == 0
    assert first["rejected"] == 1
    assert first["duplicate"] == 1

    second = database_client.post(
        "/data/import",
        files={
            "file": (
                "second.csv",
                b"symbol,trade_date,open,high,low,close,volume\nGP,2026-06-10,282,287,280,286,520000\n",
                "text/csv",
            )
        },
    ).json()

    assert second["inserted"] == 0
    assert second["updated"] == 1


def test_data_status_reads_empty_database(database_client: TestClient) -> None:
    payload = database_client.get("/data/status").json()

    assert payload["data_available"] is False
    assert payload["data_source"] == "database"
    assert payload["symbols_count"] == 0
    assert payload["rows_count"] == 0
    assert payload["earliest_trade_date"] is None
    assert payload["latest_trade_date"] is None


def test_invalid_rows_are_rejected(database_client: TestClient) -> None:
    payload = database_client.post(
        "/data/import",
        files={
            "file": (
                "invalid.csv",
                b"symbol,trade_date,open,high,low,close,volume\nACI,2026-07-20,10,8,9,10.5,1000\n",
                "text/csv",
            )
        },
    ).json()

    assert payload["ok"] is False
    assert payload["inserted"] == 0
    assert payload["rejected"] == 1
    assert "high must not be lower than low" in payload["errors"][0]


def test_collector_without_source_fails_closed(database_client: TestClient) -> None:
    response = database_client.post("/collector/run", json={"trade_date": "2026-07-20"})

    assert response.status_code == 503
    assert "no verified production source adapter" in response.json()["detail"]

    status = database_client.get("/collector/status").json()
    assert status["enabled"] is False
    assert status["running"] is False
    assert status["last_error"] is not None


def test_collector_start_stop_require_admin(raw_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", "correct-secret")

    assert raw_client.post("/collector/start").status_code == 403
    assert raw_client.post("/collector/stop").status_code == 403
