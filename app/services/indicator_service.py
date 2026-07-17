"""Lightweight deterministic technical indicators using the standard library."""

from dataclasses import dataclass

from app.schemas.ohlc import OhlcRow


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    sma20: float
    sma50: float
    ema20: float
    ema50: float
    rsi14: float
    average_volume20: float
    volume_ratio: float
    high20: float
    low20: float
    prior_high20: float
    previous_rsi14: float


class IndicatorService:
    @staticmethod
    def sma(values: list[float], period: int) -> float:
        if len(values) < period:
            raise ValueError(f"At least {period} values are required for SMA.")
        return sum(values[-period:]) / period

    @staticmethod
    def ema(values: list[float], period: int) -> float:
        if len(values) < period:
            raise ValueError(f"At least {period} values are required for EMA.")
        seed = sum(values[:period]) / period
        multiplier = 2 / (period + 1)
        result = seed
        for value in values[period:]:
            result = (value - result) * multiplier + result
        return result

    @staticmethod
    def rsi(values: list[float], period: int = 14) -> float:
        if len(values) < period + 1:
            raise ValueError(f"At least {period + 1} values are required for RSI.")
        changes = [values[index] - values[index - 1] for index in range(1, len(values))]
        gains = [max(change, 0.0) for change in changes]
        losses = [max(-change, 0.0) for change in changes]
        average_gain = sum(gains[:period]) / period
        average_loss = sum(losses[:period]) / period
        for gain, loss in zip(gains[period:], losses[period:], strict=True):
            average_gain = ((average_gain * (period - 1)) + gain) / period
            average_loss = ((average_loss * (period - 1)) + loss) / period
        if average_loss == 0:
            return 100.0 if average_gain > 0 else 50.0
        relative_strength = average_gain / average_loss
        return 100 - (100 / (1 + relative_strength))

    def calculate(self, rows: list[OhlcRow]) -> IndicatorSnapshot:
        if len(rows) < 60:
            raise ValueError("At least 60 OHLC rows are required.")
        closes = [row.close for row in rows]
        latest_window = rows[-20:]
        prior_window = rows[-21:-1] if len(rows) >= 21 else rows[-20:]
        average_volume = sum(row.volume for row in latest_window) / 20
        volume_ratio = 0.0 if average_volume <= 0 else rows[-1].volume / average_volume
        return IndicatorSnapshot(
            sma20=self.sma(closes, 20),
            sma50=self.sma(closes, 50),
            ema20=self.ema(closes, 20),
            ema50=self.ema(closes, 50),
            rsi14=self.rsi(closes, 14),
            average_volume20=average_volume,
            volume_ratio=volume_ratio,
            high20=max(row.high for row in latest_window),
            low20=min(row.low for row in latest_window),
            prior_high20=max(row.high for row in prior_window),
            previous_rsi14=self.rsi(closes[:-1], 14),
        )
