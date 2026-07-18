"""Scanner integration tests for strict qualification behavior."""

from fastapi.testclient import TestClient


def test_scanner_never_marks_failed_hard_gate_as_ready(imported_client: TestClient) -> None:
    result = imported_client.post("/scanner/run")
    assert result.status_code == 200
    payload = result.json()

    for item in payload["candidates"]:
        if item["signal_status"] == "qualified":
            assert item["grade"] in {"A+", "A"}
            assert item["qualification_passed"] is True
            assert item["entry_status"] == "READY"
            assert item["trend"] == "BULLISH"
            assert item["volume_ratio"] >= 1.5
            assert item["risk_reward"] >= 1.5
            assert item["entry_distance_percent"] is not None
            assert item["entry_distance_percent"] <= 3.0
            assert item["qualification_failures"] == []
        elif item["grade"] in {"A+", "A"}:
            assert item["entry_status"] == "NOT_READY"
            assert item["qualification_passed"] is False
            assert item["qualification_failures"]


def test_signals_endpoint_exposes_only_qualified_a_or_a_plus_and_b_plus_watch(
    imported_client: TestClient,
) -> None:
    imported_client.post("/scanner/run")
    response = imported_client.get("/signals")
    assert response.status_code == 200

    for item in response.json()["signals"]:
        if item["signal_status"] == "qualified":
            assert item["grade"] in {"A+", "A"}
            assert item["qualification_passed"] is True
            assert item["entry_status"] == "READY"
        else:
            assert item["signal_status"] == "watch"
            assert item["grade"] == "B+"
            assert item["qualification_passed"] is False
            assert item["entry_status"] == "WATCH"
