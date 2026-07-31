"""Regression tests for atomic OHLC repository merges."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from app.schemas.ohlc import OhlcRow
from app.services.csv_ingestion_service import (
    NORMALIZED_HEADERS,
    CsvParseResult,
)
from app.services.ohlc_repository import OhlcRepository


def _result(symbol: str, trade_date: date, close: float) -> CsvParseResult:
    return CsvParseResult(
        filename=f"{symbol}.csv",
        detected_headers=list(NORMALIZED_HEADERS),
        valid_rows=[
            OhlcRow(
                symbol=symbol,
                trade_date=trade_date,
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000,
                trade=None,
                value=None,
            )
        ],
        invalid_rows=0,
        warnings=[],
        errors=[],
    )


def test_merge_and_save_preserves_existing_rows(tmp_path: Path) -> None:
    repository = OhlcRepository(tmp_path / "ohlc.csv")

    inserted, updated, _ = repository.merge_and_save(
        _result("ACI", date(2026, 7, 29), 100)
    )
    assert (inserted, updated) == (1, 0)

    inserted, updated, merged = repository.merge_and_save(
        _result("BRACBANK", date(2026, 7, 29), 50)
    )

    assert (inserted, updated) == (1, 0)
    assert {(row.symbol, row.trade_date) for row in merged.valid_rows} == {
        ("ACI", date(2026, 7, 29)),
        ("BRACBANK", date(2026, 7, 29)),
    }


def test_concurrent_merges_do_not_lose_rows(tmp_path: Path) -> None:
    repository = OhlcRepository(tmp_path / "ohlc.csv")
    batches = [
        _result("ACI", date(2026, 7, 29), 100),
        _result("BRACBANK", date(2026, 7, 29), 50),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(repository.merge_and_save, batches))

    rows = repository.get_all_rows()
    assert {(row.symbol, row.trade_date) for row in rows} == {
        ("ACI", date(2026, 7, 29)),
        ("BRACBANK", date(2026, 7, 29)),
    }


def test_existing_key_is_counted_as_update(tmp_path: Path) -> None:
    repository = OhlcRepository(tmp_path / "ohlc.csv")
    repository.merge_and_save(_result("ACI", date(2026, 7, 29), 100))

    inserted, updated, merged = repository.merge_and_save(
        _result("ACI", date(2026, 7, 29), 105)
    )

    assert (inserted, updated) == (0, 1)
    assert len(merged.valid_rows) == 1
    assert merged.valid_rows[0].close == 105
