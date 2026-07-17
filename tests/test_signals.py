"""Deterministic signal endpoint tests."""

from fastapi.testclient import TestClient

EXPECTED_SYMBOLS = ["SQURPHARMA", "GP", "BATBC", "CITYBANK", "BRACBANK"]


def _signals_by_symbol(client: TestClient) -> dict[str, dict[str, object]]:
    response = client.get("/signals")
    assert response.status_code == 200
    return {item["symbol"]: item for item in response.json()["signals"]}


def test_signals_are_deterministic(client: TestClient) -> None:
    first = client.get("/signals")
    second = client.get("/signals")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert [item["symbol"] for item in first.json()["signals"]] == EXPECTED_SYMBOLS
    assert first.json()["rules"] == {
        "A+": "95-100",
        "A": "90-94",
        "B+": "85-89 watch only",
        "Reject": "below 85",
    }


def test_b_plus_is_watch_not_qualified(client: TestClient) -> None:
    citybank = _signals_by_symbol(client)["CITYBANK"]

    assert citybank["grade"] == "B+"
    assert citybank["signal_status"] == "watch"
    assert citybank["signal_status"] != "qualified"


def test_reject_is_rejected(client: TestClient) -> None:
    bracbank = _signals_by_symbol(client)["BRACBANK"]

    assert bracbank["grade"] == "Reject"
    assert bracbank["signal_status"] == "rejected"
