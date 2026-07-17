from fastapi.testclient import TestClient


def test_signals_use_latest_scanner_result(imported_client: TestClient) -> None:
    latest = imported_client.post("/scanner/run").json()
    payload = imported_client.get("/signals").json()
    expected = [
        item["symbol"]
        for item in latest["candidates"]
        if item["signal_status"] in {"qualified", "watch"}
    ]
    assert payload["data_source"] == "local_csv"
    assert [item["symbol"] for item in payload["signals"]] == expected
    assert all(item["signal_status"] != "rejected" for item in payload["signals"])
