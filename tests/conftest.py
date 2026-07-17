"""Shared test fixtures with isolated local storage."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Point every test at a fresh temporary OHLC storage file."""

    storage_path = tmp_path / "storage" / "dse_ohlc.csv"
    monkeypatch.setenv("OHLC_STORAGE_PATH", str(storage_path))
    get_settings.cache_clear()
    yield storage_path
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Return an isolated FastAPI test client."""

    return TestClient(app)
