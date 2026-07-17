"""SQLite-backed proof for the optional SQLAlchemy repositories."""

from fastapi.testclient import TestClient
from sqlalchemy import UniqueConstraint

from app.db.models import OhlcDaily


def test_ohlc_unique_constraint_is_declared() -> None:
    constraints = [
        constraint
        for constraint in OhlcDaily.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    columns = [{column.name for column in constraint.columns} for constraint in constraints]
    assert {"symbol", "trade_date"} in columns


def test_import_db_upserts_and_database_reads(database_client: TestClient) -> None:
    first_csv = (
        b"symbol,trade_date,open,high,low,close,volume\n"
        b"GP,2026-06-10,280,286,278,284.5,510000\n"
        b"GP,2026-06-11,284,290,282,288,600000\n"
        b"BATBC,2026-06-11,420,425,418,423,100000\n"
    )
    first = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("first.csv", first_csv, "text/csv")},
    ).json()
    assert first["ok"] is True
    assert first["inserted_rows"] == 3
    assert first["updated_rows"] == 0

    updated_csv = (
        b"symbol,trade_date,open,high,low,close,volume\n"
        b"GP,2026-06-11,285,291,283,289,610000\n"
        b"SQURPHARMA,2026-06-11,210,215,208,212,200000\n"
    )
    second = database_client.post(
        "/data/ohlc/import-db",
        files={"file": ("second.csv", updated_csv, "text/csv")},
    ).json()
    assert second["inserted_rows"] == 1
    assert second["updated_rows"] == 1

    symbols = database_client.get("/symbols").json()
    assert symbols == {
        "data_source": "database",
        "symbols_count": 3,
        "symbols": ["BATBC", "GP", "SQURPHARMA"],
    }
    ohlc = database_client.get("/ohlc/gp?source=database").json()
    assert ohlc["data_source"] == "database"
    assert ohlc["rows"][0]["close"] == 289.0
    status = database_client.get("/status").json()
    assert status["database_connected"] is True
    assert status["data_source"] == "database"
    assert status["symbols_count"] == 3
    assert status["rows_count"] == 4


def test_database_source_endpoint(database_client: TestClient) -> None:
    payload = database_client.get("/data/source").json()
    assert payload["preferred_source"] == "database"
    assert payload["database_available"] is True
    assert payload["fallback_order"] == ["database", "local_csv", "demo"]
