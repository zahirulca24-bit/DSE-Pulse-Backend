from datetime import date, timedelta

from app.schemas.ohlc import OhlcRow
from app.services.indicator_service import IndicatorService


def test_indicator_snapshot_contains_required_values() -> None:
    rows = [
        OhlcRow(
            symbol="GP",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            volume=1000 + index * 10,
        )
        for index in range(60)
    ]
    result = IndicatorService().calculate(rows)
    assert result.sma20 > 0
    assert result.sma50 > 0
    assert result.ema20 > 0
    assert result.ema50 > 0
    assert 0 <= result.rsi14 <= 100
    assert result.average_volume20 > 0
    assert result.volume_ratio > 0
    assert result.high20 > result.low20
