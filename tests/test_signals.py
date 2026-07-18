"""Signal endpoint tests: real persisted scanner data only, never demo fallback."""

from fastapi.testclient import TestClient


def test_signals_are_empty_without_real_scanner_result(client: TestClient) -> None:
    first = client.get("/signals")
    second = client.get("/signals")

    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert payload["mode"] == "no_scan"
    assert payload["data_source"] == "none"
    assert payload["signals"] == []
    assert payload["rules"] == {
        "A+": "95-100",
        "A": "90-94",
        "B+": "85-89 watch only",
        "Reject": "below 85",
    }
    assert "No real scanner result exists" in payload["message"]


def test_signals_use_real_scanner_result_after_scan(imported_client: TestClient) -> None:
    latest = imported_client.post("/scanner/run").json()
    payload = imported_client.get("/signals").json()

    expected = [
        item["symbol"]
        for item in latest["candidates"]
        if item["signal_status"] in {"qualified", "watch"}
    ]
    assert payload["data_source"] == "local_csv"
    assert payload["mode"] == "local_csv"
    assert [item["symbol"] for item in payload["signals"]] == expected
    assert all(item["signal_status"] != "rejected" for item in payload["signals"])
    assert all(item.get("data_mode") != "Demo Data" for item in payload["signals"])
