from fastapi.testclient import TestClient


def test_latest_before_run_returns_no_scan(client: TestClient) -> None:
    payload = client.get("/scanner/latest").json()
    assert payload["ok"] is False
    assert payload["mode"] == "no_scan"
    assert payload["candidates"] == []


def test_scanner_status_after_run(imported_client: TestClient) -> None:
    imported_client.post("/scanner/run")
    payload = imported_client.get("/scanner/status").json()
    assert payload["scanner_ready"] is True
    assert payload["mode"] == "local_csv"
    assert payload["data_available"] is True
    assert payload["latest_scan_available"] is True
    assert payload["execution_enabled"] is False


def test_successful_data_import_invalidates_previous_scan(
    imported_client: TestClient,
    scanner_csv: bytes,
) -> None:
    assert imported_client.post("/scanner/run").json()["ok"] is True
    assert imported_client.get("/scanner/latest").json()["ok"] is True

    imported = imported_client.post(
        "/data/ohlc/import",
        files={"file": ("replacement.csv", scanner_csv, "text/csv")},
    )
    assert imported.json()["ok"] is True
    latest = imported_client.get("/scanner/latest").json()
    assert latest["ok"] is False
    assert latest["mode"] == "no_scan"
