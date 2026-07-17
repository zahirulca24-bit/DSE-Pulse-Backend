"""Protected collector endpoint and database upsert tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.repositories.collector_repository import CollectorRepository
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.schemas.ohlc import OhlcRow
from app.services.collector_service import CollectorService
from app.services.collector_source import CollectorBatch
from app.services.data_audit_service import DataAuditService
from app.services.dependencies import get_collector_service, get_database_manager
from tests.conftest import build_symbol_rows, csv_bytes


class FakeCollectorSource:
    """Return deterministic rows without making an external network request."""

    name = "fake-dse-source"

    def collect_range(
        self,
        start_date: date,
        end_date: date,
        allowed_symbols: set[str],
    ) -> CollectorBatch:
        selected = sorted(allowed_symbols)[:1]
        rows: list[OhlcRow] = []
        candidate = start_date
        while candidate <= end_date:
            if candidate.weekday() not in (4, 5):
                rows.extend(
                    OhlcRow(
                        symbol=symbol,
                        trade_date=candidate,
                        open=101.0,
                        high=104.0,
                        low=100.0,
                        close=103.0,
                        volume=150_000,
                        trade=500,
                        value=15_450_000,
                    )
                    for symbol in selected
                )
            candidate += timedelta(days=1)
        return CollectorBatch(
            rows=rows,
            fetched_rows=len(rows),
            invalid_rows=0,
            missing_symbols=sorted(allowed_symbols - set(selected)),
            warnings=[],
        )


def _collector_service() -> CollectorService:
    manager = get_database_manager()
    return CollectorService(
        settings=get_settings(),
        repository=CollectorRepository(manager),
        ohlc_repository=OhlcDbRepository(manager),
        audit_service=DataAuditService(manager),
        source=FakeCollectorSource(),
    )


def _seed_database(client: TestClient) -> None:
    rows = build_symbol_rows("ALPHA", days=65)
    rows += build_symbol_rows("BETA", days=65)
    response = client.post(
        "/data/ohlc/import-db",
        files={"file": ("seed.csv", csv_bytes(rows), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_collector_requires_backend_admin_token(database_client: TestClient) -> None:
    response = database_client.post("/collector/run", json={"trade_date": "2026-07-01"})

    assert response.status_code == 503
    assert "COLLECTOR_ADMIN_TOKEN" in response.json()["detail"]


def test_collector_rejects_invalid_token(
    database_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        response = database_client.post(
            "/collector/run",
            json={"trade_date": "2026-07-01"},
            headers={"X-Collector-Token": "wrong-secret"},
        )
    finally:
        app.dependency_overrides.pop(get_collector_service, None)
        get_settings.cache_clear()

    assert response.status_code == 403


def test_collector_runs_in_background_and_upserts_database(
    database_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_database(database_client)
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        queued = database_client.post(
            "/collector/run",
            json={"trade_date": "2026-07-01", "collect_missing": False},
            headers={"X-Collector-Token": "server-secret"},
        )
        latest = database_client.get("/collector/latest")
        history = database_client.get("/collector/history?limit=5")
    finally:
        app.dependency_overrides.pop(get_collector_service, None)
        get_settings.cache_clear()

    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "completed"
    assert payload["requested_trade_date"] == "2026-07-01"
    assert payload["source"] == "fake-dse-source"
    assert payload["collected_symbols"] == 1
    assert payload["inserted_rows"] == 1
    assert payload["updated_rows"] == 0
    assert payload["missing_symbols"] == ["BETA"]
    assert payload["scanner_refresh_required"] is True
    assert history.status_code == 200
    assert history.json()["count"] == 1


def test_collector_rejects_future_date(
    database_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_database(database_client)
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        response = database_client.post(
            "/collector/run",
            json={"trade_date": "2099-01-01"},
            headers={"X-Collector-Token": "server-secret"},
        )
    finally:
        app.dependency_overrides.pop(get_collector_service, None)
        get_settings.cache_clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "Future trade dates are not allowed."
