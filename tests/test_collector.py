"""Protected collector endpoint tests for the Vercel Blob production path."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas.ohlc import OhlcRow
from app.services.collector_job_repository import CollectorJobRepository
from app.services.collector_service import CollectorService
from app.services.collector_source import CollectorBatch
from app.services.csv_ingestion_service import CsvParseResult
from app.services.dependencies import get_collector_service
from app.services.vercel_blob_client import VercelBlobStatus


class FakeCollectorSource:
    """Return one deterministic approved symbol without external network access."""

    name = "fake-dse-source"

    def collect_range(
        self,
        start_date: date,
        end_date: date,
        allowed_symbols: set[str],
    ) -> CollectorBatch:
        symbol = "ACI"
        assert symbol in allowed_symbols
        row = OhlcRow(
            symbol=symbol,
            trade_date=end_date,
            open=101.0,
            high=104.0,
            low=100.0,
            close=103.0,
            volume=150_000,
            trade=500,
            value=15_450_000,
        )
        return CollectorBatch(
            rows=[row],
            fetched_rows=1,
            invalid_rows=0,
            missing_symbols=sorted(allowed_symbols - {symbol}),
            warnings=[],
        )


class FakeBlobRepository:
    """Minimal connected Blob repository used by endpoint tests."""

    def blob_status(self) -> VercelBlobStatus:
        return VercelBlobStatus(
            configured=True,
            connected=True,
            message="Blob ready.",
        )

    def sync_from_blob(self, force: bool = False) -> bool:
        return force

    def get_status(self) -> object:
        return type("Status", (), {"latest_trade_date": date(2026, 6, 30)})()

    def merge_and_save_to_blob(
        self,
        parsed: CsvParseResult,
    ) -> tuple[int, int, CsvParseResult]:
        return len(parsed.valid_rows), 0, parsed


def _collector_service() -> CollectorService:
    settings = get_settings()
    return CollectorService(
        settings=settings,
        repository=CollectorJobRepository(settings.collector_storage_path),
        ohlc_repository=FakeBlobRepository(),  # type: ignore[arg-type]
        source=FakeCollectorSource(),
    )


def test_collector_requires_backend_admin_token(client: TestClient) -> None:
    response = client.post("/collector/run", json={"trade_date": "2026-07-01"})

    assert response.status_code == 503
    assert "COLLECTOR_ADMIN_TOKEN" in response.json()["detail"]


def test_collector_rejects_invalid_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        response = client.post(
            "/collector/run",
            json={"trade_date": "2026-07-01"},
            headers={"X-Collector-Token": "wrong-secret"},
        )
    finally:
        app.dependency_overrides.pop(get_collector_service, None)
        get_settings.cache_clear()

    assert response.status_code == 403


def test_collector_runs_in_background_and_updates_blob_master(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        queued = client.post(
            "/collector/run",
            json={"trade_date": "2026-07-01", "collect_missing": False},
            headers={"X-Collector-Token": "server-secret"},
        )
        latest = client.get("/collector/latest")
        history = client.get("/collector/history?limit=5")
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
    assert payload["scanner_refresh_required"] is True
    assert any("Vercel Blob master updated" in item for item in payload["warnings"])
    assert history.status_code == 200
    assert history.json()["count"] == 1


def test_collector_rejects_future_date(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "server-secret")
    get_settings.cache_clear()
    app.dependency_overrides[get_collector_service] = _collector_service
    try:
        response = client.post(
            "/collector/run",
            json={"trade_date": "2099-01-01"},
            headers={"X-Collector-Token": "server-secret"},
        )
    finally:
        app.dependency_overrides.pop(get_collector_service, None)
        get_settings.cache_clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "Future trade dates are not allowed."
