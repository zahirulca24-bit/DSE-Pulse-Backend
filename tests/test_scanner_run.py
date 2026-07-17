from fastapi.testclient import TestClient

from tests.conftest import build_symbol_rows, csv_bytes


def test_scanner_run_returns_no_data(client: TestClient) -> None:
    response = client.post("/scanner/run")
    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["mode"] == "no_data"
    assert payload["candidates"] == []


def test_scanner_run_generates_and_stores_result(imported_client: TestClient) -> None:
    payload = imported_client.post("/scanner/run").json()
    assert payload["ok"] is True
    assert payload["data_source"] == "local_csv"
    assert payload["scanned_symbols"] == 4
    assert payload["eligible_symbols"] == 4
    latest = imported_client.get("/scanner/latest").json()
    assert latest == payload


def test_insufficient_data_symbol_is_not_candidate(client: TestClient) -> None:
    data = csv_bytes(build_symbol_rows("GP", days=59))
    assert client.post("/data/ohlc/import", files={"file": ("short.csv", data, "text/csv")}).json()["ok"]
    payload = client.post("/scanner/run").json()
    assert payload["scanned_symbols"] == 1
    assert payload["eligible_symbols"] == 0
    assert payload["candidates"] == []


def test_candidate_count_is_capped_at_50(client: TestClient) -> None:
    rows: list[dict[str, str]] = []
    for index in range(55):
        rows += build_symbol_rows(f"SYM{index:02d}", final_volume_multiplier=1.2)
    data = csv_bytes(rows)
    assert client.post("/data/ohlc/import", files={"file": ("many.csv", data, "text/csv")}).json()["ok"]
    payload = client.post("/scanner/run").json()
    assert payload["scanned_symbols"] == 55
    assert len(payload["candidates"]) == 50
