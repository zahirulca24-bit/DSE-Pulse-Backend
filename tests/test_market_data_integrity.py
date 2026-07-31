"""Regression tests for deterministic OHLC CSV ingestion integrity."""

from app.services.csv_ingestion_service import CsvIngestionService


def _csv(*rows: str) -> str:
    return "\n".join(
        [
            "symbol,trade_date,open,high,low,close,volume,trade,value",
            *rows,
        ]
    )


def test_duplicate_symbol_date_keeps_first_valid_row_only() -> None:
    result = CsvIngestionService().parse_text(
        _csv(
            "SQURPHARMA,2026-07-30,100,110,95,105,1000,,",
            "SQURPHARMA,2026-07-30,101,111,96,106,2000,,",
        ),
        "duplicate.csv",
    )

    assert result.ok is True
    assert result.invalid_rows == 1
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0].open == 100
    assert result.valid_rows[0].volume == 1000
    assert "Duplicate symbol/trade_date rows discarded: 1." in result.warnings


def test_zero_or_negative_price_rows_are_rejected() -> None:
    result = CsvIngestionService().parse_text(
        _csv(
            "ACI,2026-07-30,0,110,95,105,1000,,",
            "BRACBANK,2026-07-30,100,110,-1,105,1000,,",
        ),
        "invalid-price.csv",
    )

    assert result.ok is False
    assert result.invalid_rows == 2
    assert result.valid_rows == []
    assert any("must be greater than zero" in error for error in result.errors)


def test_open_and_close_must_be_inside_daily_range() -> None:
    result = CsvIngestionService().parse_text(
        _csv(
            "ACI,2026-07-30,120,110,95,105,1000,,",
            "BRACBANK,2026-07-30,100,110,95,90,1000,,",
        ),
        "range-invalid.csv",
    )

    assert result.ok is False
    assert result.invalid_rows == 2
    assert any("open must be inside" in error for error in result.errors)
    assert any("close must be inside" in error for error in result.errors)


def test_unique_valid_rows_remain_importable() -> None:
    result = CsvIngestionService().parse_text(
        _csv(
            "ACI,2026-07-30,100,110,95,105,0,,",
            "BRACBANK,2026-07-30,50,55,49,54,500,,",
        ),
        "valid.csv",
    )

    assert result.ok is True
    assert result.invalid_rows == 0
    assert len(result.valid_rows) == 2
    assert "Zero volume rows detected: 1." in result.warnings
