"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health_returns_http_200(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "DSE Pulse Backend",
        "version": "0.1.0",
        "mode": "demo",
        "market": "DSE",
        "market_open_now": False,
    }
