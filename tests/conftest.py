"""Shared test fixtures with isolated local storage and scanner data builders."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.main import app
from app.services.dependencies import get_database_manager

_TEST_ADMIN_TOKEN = "test-backend-admin-token"


def build_symbol_rows(symbol: str, *, days: int = 65, start: float = 100.0, drift: float = 0.35,
    swing: float = 0.8, final_volume_multiplier: float = 1.0, high_gap: float = 0.5,
    low_gap: float = 1.0, final_high_gap: float | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current = start
    start_date = date(2026, 1, 1)
    for index in range(days):
        current += drift + (swing if index % 2 == 0 else -swing)
        close = max(current, 1.0)
        volume = int(100_000 * final_volume_multiplier) if index == days - 1 else 100_000
        effective_high_gap = final_high_gap if index == days - 1 and final_high_gap is not None else high_gap
        rows.append({"symbol": symbol, "trade_date": (start_date + timedelta(days=index)).isoformat(),
            "open": f"{close - 0.2:.4f}", "high": f"{close + effective_high_gap:.4f}",
            "low": f"{close - low_gap:.4f}", "close": f"{close:.4f}", "volume": str(volume),
            "trade": "", "value": ""})
    return rows


def csv_bytes(rows: list[dict[str, str]]) -> bytes:
    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=["symbol", "trade_date", "open", "high", "low", "close", "volume", "trade", "value"])
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode()


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    try:
        get_database_manager().dispose()
    finally:
        get_database_manager.cache_clear()
    storage_dir = tmp_path / "storage"
    ohlc_path = storage_dir / "dse_ohlc.csv"
    monkeypatch.setenv("OHLC_STORAGE_PATH", str(ohlc_path))
    monkeypatch.setenv("SCANNER_STORAGE_PATH", str(storage_dir / "scanner_latest.json"))
    monkeypatch.setenv("COLLECTOR_STORAGE_PATH", str(storage_dir / "collector_jobs.json"))
    monkeypatch.setenv("BACKEND_ADMIN_TOKEN", _TEST_ADMIN_TOKEN)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    get_settings.cache_clear()
    yield ohlc_path
    try:
        get_database_manager().dispose()
    finally:
        get_database_manager.cache_clear()
        get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    test_client = TestClient(app)
    test_client.headers.update({"X-Admin-Token": _TEST_ADMIN_TOKEN})
    return test_client


@pytest.fixture
def scanner_csv() -> bytes:
    rows: list[dict[str, str]] = []
    rows += build_symbol_rows("SQURPHARMA", drift=0.1, final_volume_multiplier=2.5, final_high_gap=8.0)
    rows += build_symbol_rows("ACI", drift=0.1, final_volume_multiplier=1.7, final_high_gap=4.0)
    rows += build_symbol_rows("CITYBANK", drift=0.1, final_volume_multiplier=0.9, final_high_gap=8.0)
    rows += build_symbol_rows("BRACBANK", drift=-0.15, swing=0.4, final_volume_multiplier=0.5)
    return csv_bytes(rows)


@pytest.fixture
def imported_client(client: TestClient, scanner_csv: bytes) -> TestClient:
    response = client.post("/data/ohlc/import", files={"file": ("scanner.csv", scanner_csv, "text/csv")})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    return client


@pytest.fixture
def database_client(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    database_path = tmp_path / "test_database.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    get_settings.cache_clear()
    get_database_manager.cache_clear()
    assert initialize_database(get_database_manager()) is True
    return client
