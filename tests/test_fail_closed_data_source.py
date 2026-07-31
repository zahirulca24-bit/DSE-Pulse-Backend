"""Regression tests for verified-only DSE market-data source selection."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.database import DataSourceResponse


def test_data_source_fails_closed_without_verified_market_data(
    client: TestClient,
) -> None:
    response = client.get("/data/source")

    assert response.status_code == 200
    assert response.json() == {
        "preferred_source": "none",
        "database_available": False,
        "local_csv_available": False,
        "market_data_available": False,
        "fallback_order": [],
        "message": "No verified DSE market-data source is available.",
    }
    assert "demo" not in response.text.lower()


def test_data_source_contract_rejects_demo_market_data() -> None:
    with pytest.raises(ValidationError):
        DataSourceResponse(
            preferred_source="demo",
            database_available=False,
            local_csv_available=False,
            market_data_available=False,
            fallback_order=["demo"],
            message="Demo data.",
        )


def test_verified_local_csv_source_has_no_synthetic_fallback() -> None:
    response = DataSourceResponse(
        preferred_source="local_csv",
        database_available=False,
        local_csv_available=True,
        market_data_available=True,
        fallback_order=["local_csv"],
        message="Local CSV OHLC data is active.",
    )

    assert response.preferred_source == "local_csv"
    assert response.fallback_order == ["local_csv"]
    assert response.market_data_available is True
