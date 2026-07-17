from fastapi.testclient import TestClient


def test_candidates_no_scan_is_clear(client: TestClient) -> None:
    payload = client.get("/scanner/candidates").json()
    assert payload["ok"] is False
    assert payload["mode"] == "no_scan"


def test_candidates_filter_by_grade_and_status(imported_client: TestClient) -> None:
    latest = imported_client.post("/scanner/run").json()
    grades = {item["grade"] for item in latest["candidates"]}
    for grade in grades:
        payload = imported_client.get("/scanner/candidates", params={"grade": grade}).json()
        assert all(item["grade"] == grade for item in payload["candidates"])
    for status in {item["signal_status"] for item in latest["candidates"]}:
        payload = imported_client.get("/scanner/candidates", params={"signal_status": status}).json()
        assert all(item["signal_status"] == status for item in payload["candidates"])


def test_central_grade_status_contract(imported_client: TestClient) -> None:
    candidates = imported_client.post("/scanner/run").json()["candidates"]
    for item in candidates:
        if item["grade"] in {"A+", "A"}:
            assert item["signal_status"] == "qualified"
        elif item["grade"] == "B+":
            assert item["signal_status"] == "watch"
        else:
            assert item["signal_status"] == "rejected"


def test_candidate_text_has_no_prohibited_action_words(imported_client: TestClient) -> None:
    candidates = imported_client.post("/scanner/run").json()["candidates"]
    prohibited = {"buy", "sell", "order", "execute"}
    for candidate in candidates:
        text = " ".join([candidate["setup"], *candidate["reasons"], *candidate["warnings"]]).lower()
        assert not any(word in text for word in prohibited)


def test_engine_generates_all_locked_status_classes(imported_client: TestClient) -> None:
    candidates = imported_client.post("/scanner/run").json()["candidates"]
    by_symbol = {item["symbol"]: item for item in candidates}
    assert by_symbol["SQURPHARMA"]["grade"] == "A+"
    assert by_symbol["SQURPHARMA"]["signal_status"] == "qualified"
    assert by_symbol["GP"]["grade"] == "A"
    assert by_symbol["GP"]["signal_status"] == "qualified"
    assert by_symbol["CITYBANK"]["grade"] == "B+"
    assert by_symbol["CITYBANK"]["signal_status"] == "watch"
    assert by_symbol["BRACBANK"]["grade"] == "Reject"
    assert by_symbol["BRACBANK"]["signal_status"] == "rejected"
