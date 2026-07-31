"""Deterministic local CSV scanner engine."""

from collections import defaultdict
from datetime import UTC, datetime

from app.core.qualification_rules import evaluate_qualification
from app.core.signal_rules import SignalStatus, classify_score
from app.data.symbol_metadata import SYMBOL_SECTORS
from app.schemas.ohlc import OhlcRow
from app.schemas.scanner_result import (
    EntryStatus,
    ScannerCandidate,
    ScannerResultResponse,
    SetupType,
    TrendType,
)
from app.services.indicator_service import IndicatorService, IndicatorSnapshot

_MINIMUM_ROWS = 60
_MAX_CANDIDATES = 50


class ScannerEngine:
    def __init__(self, indicator_service: IndicatorService | None = None) -> None:
        self._indicators = indicator_service or IndicatorService()

    def run(self, rows: list[OhlcRow], source: str = "local_csv") -> ScannerResultResponse:
        grouped: dict[str, list[OhlcRow]] = defaultdict(list)
        for row in rows:
            grouped[row.symbol].append(row)
        all_candidates: list[ScannerCandidate] = []
        eligible_symbols = 0
        for symbol in sorted(grouped):
            symbol_rows = sorted(grouped[symbol], key=lambda row: row.trade_date)
            if len(symbol_rows) < _MINIMUM_ROWS:
                continue
            eligible_symbols += 1
            all_candidates.append(self._candidate(symbol, symbol_rows, source))
        qualified = sum(candidate.signal_status == "qualified" for candidate in all_candidates)
        watch = sum(candidate.signal_status == "watch" for candidate in all_candidates)
        rejected = sum(candidate.signal_status == "rejected" for candidate in all_candidates)
        all_candidates.sort(key=self._sort_key)
        selected = all_candidates[:_MAX_CANDIDATES]
        if rejected and selected and not any(item.signal_status == "rejected" for item in selected):
            highest_reject = next(item for item in all_candidates if item.signal_status == "rejected")
            selected[-1] = highest_reject
            selected.sort(key=self._sort_key)
        skipped_symbols = len(grouped) - eligible_symbols
        message = "Local CSV scan completed with strict qualification gates."
        if skipped_symbols:
            message += f" {skipped_symbols} symbol(s) skipped because fewer than {_MINIMUM_ROWS} rows were available."
        if eligible_symbols == 0:
            message = "No symbols had the minimum 60 OHLC rows required for scanner calculations."
        return ScannerResultResponse(
            ok=True,
            mode="database" if source == "database" else "local_csv",
            data_source="database" if source == "database" else "local_csv",
            scanned_symbols=len(grouped),
            eligible_symbols=eligible_symbols,
            qualified_count=qualified,
            watch_count=watch,
            rejected_count=rejected,
            generated_at=datetime.now(UTC),
            message=message,
            candidates=selected,
        )

    def _candidate(self, symbol: str, rows: list[OhlcRow], source: str) -> ScannerCandidate:
        latest = rows[-1]
        indicators = self._indicators.calculate(rows)
        trend = self._trend(latest.close, indicators)
        setup = self._setup(latest.close, indicators, trend)
        risk_reward = self._risk_reward(
            setup=setup,
            close=latest.close,
            support=indicators.low20,
            resistance=indicators.high20,
            prior_high20=indicators.prior_high20,
        )
        score, reasons = self._score(latest.close, latest.volume, indicators, setup, risk_reward)
        grade, _raw_status = classify_score(score)
        decision = evaluate_qualification(
            grade=grade,
            trend=trend,
            setup=setup,
            close=latest.close,
            ema20=indicators.ema20,
            sma20=indicators.sma20,
            prior_high20=indicators.prior_high20,
            volume_ratio=indicators.volume_ratio,
            risk_reward=risk_reward,
            latest_volume=latest.volume,
        )
        signal_status = decision.status
        warnings: list[str] = []
        sector = SYMBOL_SECTORS.get(symbol)
        if sector is None:
            warnings.append("Sector metadata is unavailable for this symbol.")
        if decision.passed:
            reasons.append("Strict qualification gate passed.")
        else:
            warnings.extend(decision.failures)
        return ScannerCandidate(
            symbol=symbol,
            sector=sector,
            grade=grade,
            score=score,
            signal_status=signal_status,
            entry_status=self._entry_status(signal_status),
            setup=setup,
            latest_close=round(latest.close, 4),
            trade_date=latest.trade_date,
            trend=trend,
            ema20=round(indicators.ema20, 4),
            ema50=round(indicators.ema50, 4),
            sma20=round(indicators.sma20, 4),
            sma50=round(indicators.sma50, 4),
            rsi14=round(indicators.rsi14, 2),
            volume_ratio=round(indicators.volume_ratio, 2),
            risk_reward=round(risk_reward, 2),
            qualification_passed=decision.passed,
            qualification_failures=list(decision.failures),
            entry_distance_percent=(
                None
                if decision.entry_distance_ratio is None
                else round(decision.entry_distance_ratio * 100, 2)
            ),
            reasons=reasons,
            warnings=warnings,
            data_mode="Database" if source == "database" else "Local CSV",
        )

    @staticmethod
    def _trend(close: float, values: IndicatorSnapshot) -> TrendType:
        if close > values.ema20 > values.ema50 and values.sma20 > values.sma50:
            return "BULLISH"
        if close < values.ema20 < values.ema50 and values.sma20 < values.sma50:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _setup(close: float, values: IndicatorSnapshot, trend: TrendType) -> SetupType:
        if trend == "BULLISH" and close >= values.prior_high20 and values.volume_ratio >= 1.1:
            return "20-Day Breakout"
        ema_distance = 0.0 if values.ema20 == 0 else abs(close - values.ema20) / values.ema20
        if trend == "BULLISH" and close >= values.ema20 and ema_distance <= 0.03 and 45 <= values.rsi14 <= 68:
            return "EMA Trend Pullback"
        if values.previous_rsi14 < 50 <= values.rsi14 and close > values.ema20:
            return "RSI Momentum Recovery"
        if close > values.sma20 > values.sma50 and values.rsi14 >= 50:
            return "SMA Trend Continuation"
        return "Rejected / No Setup"

    @staticmethod
    def _risk_reward(
        *,
        setup: SetupType,
        close: float,
        support: float,
        resistance: float,
        prior_high20: float,
    ) -> float:
        risk = close - support
        if setup == "20-Day Breakout":
            prior_range = prior_high20 - support
            projected_target = prior_high20 + prior_range
            reward = projected_target - close
        else:
            reward = resistance - close
        if risk <= 0 or reward <= 0:
            return 0.0
        return reward / risk

    @staticmethod
    def _score(
        close: float, volume: int, values: IndicatorSnapshot, setup: SetupType, risk_reward: float
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        if close > values.ema20 > values.ema50:
            score += 30
            reasons.append("Close is above EMA20 and EMA50.")
        elif close > values.ema20 and values.ema20 >= values.ema50:
            score += 24
            reasons.append("Close remains above EMA20 with aligned averages.")
        elif close > values.ema50:
            score += 15
            reasons.append("Close is above EMA50.")
        if 50 <= values.rsi14 <= 70:
            score += 20
            reasons.append("RSI14 is in the healthy momentum range.")
        elif 45 <= values.rsi14 < 50 or 70 < values.rsi14 <= 75:
            score += 12
            reasons.append("RSI14 is near the preferred momentum range.")
        elif values.rsi14 > 40:
            score += 5
        if values.volume_ratio >= 1.5:
            score += 20
            reasons.append("Volume is at least 1.5 times the 20-day average.")
        elif values.volume_ratio >= 1.1:
            score += 14
            reasons.append("Volume is above the 20-day average.")
        elif values.volume_ratio >= 0.8:
            score += 8
        setup_scores: dict[SetupType, int] = {
            "20-Day Breakout": 20,
            "EMA Trend Pullback": 18,
            "RSI Momentum Recovery": 16,
            "SMA Trend Continuation": 14,
            "Rejected / No Setup": 0,
        }
        score += setup_scores[setup]
        if setup != "Rejected / No Setup":
            reasons.append(f"Deterministic setup: {setup}.")
        if risk_reward >= 2:
            score += 10
            reasons.append("Range-based reward/risk ratio is at least 2.0.")
        elif risk_reward >= 1:
            score += 6
            reasons.append("Range-based reward/risk ratio is at least 1.0.")
        elif risk_reward > 0:
            score += 3
        if volume == 0:
            reasons.append("Latest row has zero volume.")
        return min(score, 100), reasons

    @staticmethod
    def _entry_status(status: SignalStatus) -> EntryStatus:
        if status == "qualified":
            return "READY"
        if status == "watch":
            return "WATCH"
        return "NOT_READY"

    @staticmethod
    def _sort_key(candidate: ScannerCandidate) -> tuple[int, int, str]:
        priority = {"qualified": 0, "watch": 1, "rejected": 2}
        return (priority[candidate.signal_status], -candidate.score, candidate.symbol)
