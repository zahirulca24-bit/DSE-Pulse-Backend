"""Regression tests for zero-eligible scanner fail-closed behavior."""

from datetime import UTC, date, datetime

from app.schemas.ohlc import OhlcRow
from app.schemas.scanner_result import ScannerResultResponse
from app.services.scanner_service import ScannerService


class _Cache:
    def get_all_rows(self) -> list[OhlcRow]:
        return [
            OhlcRow(
                symbol="BRACBANK",
                trade_date=date(2026, 7, 30),
                open=48.0,
                high=49.0,
                low=47.5,
                close=48.5,
                volume=510000,
            )
        ]


class _Repository:
    def __init__(self) -> None:
        self.saved = False

    def save(self, result: ScannerResultResponse) -> None:
        self.saved = True


class _Engine:
    def __init__(self, eligible_symbols: int) -> None:
        self.eligible_symbols = eligible_symbols

    def run(
        self,
        rows: list[OhlcRow],
        source: str = "local_csv",
    ) -> ScannerResultResponse:
        return ScannerResultResponse(
            ok=True,
            mode="local_csv",
            data_source="local_csv",
            scanned_symbols=1,
            eligible_symbols=self.eligible_symbols,
            qualified_count=0,
            watch_count=0,
            rejected_count=0,
            generated_at=datetime.now(UTC),
            message="Engine completed.",
            candidates=[],
        )


def test_zero_eligible_scan_fails_closed_and_is_not_persisted() -> None:
    repository = _Repository()
    service = ScannerService(_Cache(), repository, _Engine(eligible_symbols=0))

    result = service.run()

    assert result.ok is False
    assert result.eligible_symbols == 0
    assert result.generated_at is None
    assert result.candidates == []
    assert "minimum 60 ohlc rows" in result.message.lower()
    assert repository.saved is False


def test_eligible_scan_remains_successful_and_is_persisted() -> None:
    repository = _Repository()
    service = ScannerService(_Cache(), repository, _Engine(eligible_symbols=1))

    result = service.run()

    assert result.ok is True
    assert result.eligible_symbols == 1
    assert result.generated_at is not None
    assert repository.saved is True
