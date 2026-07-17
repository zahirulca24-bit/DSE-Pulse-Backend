"""DSE market-data source adapter for manual collector jobs."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from app.schemas.ohlc import OhlcRow


class CollectorSourceError(RuntimeError):
    """Raised when the external DSE source cannot produce a safe batch."""


@dataclass(frozen=True, slots=True)
class CollectorBatch:
    """Normalized result returned by a collector source."""

    rows: list[OhlcRow]
    fetched_rows: int
    invalid_rows: int
    missing_symbols: list[str]
    warnings: list[str]


class CollectorSource(Protocol):
    """Interface implemented by external DSE data providers."""

    name: str

    def collect(self, trade_date: date, allowed_symbols: set[str]) -> CollectorBatch:
        """Fetch and normalize one completed DSE trading date."""

        ...


class BdshareCollectorSource:
    """Fetch one-day historical OHLCV through the maintained bdshare package."""

    name = "bdshare"

    def collect(self, trade_date: date, allowed_symbols: set[str]) -> CollectorBatch:
        if not allowed_symbols:
            raise CollectorSourceError("Collector universe is empty; import audited OHLC data first.")

        try:
            import bdshare  # type: ignore[import-untyped]

            fetcher = getattr(bdshare, "get_historical_data", None)
            if fetcher is None:
                fetcher = getattr(bdshare, "get_hist_data", None)
            if fetcher is None:
                raise CollectorSourceError("Installed bdshare version has no historical data function.")
            frame: Any = fetcher(trade_date.isoformat(), trade_date.isoformat())
        except CollectorSourceError:
            raise
        except Exception as exc:
            raise CollectorSourceError(f"DSE source request failed: {type(exc).__name__}.") from exc

        if frame is None or bool(getattr(frame, "empty", True)):
            raise CollectorSourceError(f"No DSE rows were returned for {trade_date.isoformat()}.")

        try:
            raw_records: list[dict[str, Any]] = frame.reset_index().to_dict(orient="records")
        except Exception as exc:
            raise CollectorSourceError("DSE source returned an unsupported table structure.") from exc

        normalized: dict[str, OhlcRow] = {}
        invalid_rows = 0
        outside_universe = 0
        wrong_date_rows = 0

        for raw in raw_records:
            item = {_normalize_key(str(key)): value for key, value in raw.items()}
            symbol = _first_text(item, ("symbol", "tradingcode", "code", "instrument"))
            row_date = _first_date(item, ("tradedate", "date", "index"))
            if not symbol or row_date is None:
                invalid_rows += 1
                continue
            symbol = symbol.upper()
            if row_date != trade_date:
                wrong_date_rows += 1
                continue
            if symbol not in allowed_symbols:
                outside_universe += 1
                continue

            open_price = _first_float(item, ("open", "openingprice"))
            high = _first_float(item, ("high", "highprice"))
            low = _first_float(item, ("low", "lowprice"))
            close = _first_float(item, ("close", "closingprice", "ltp"))
            volume = _first_int(item, ("volume", "totalvolume"))
            trade = _first_float(item, ("trade", "trades", "totaltrade"))
            value = _first_float(item, ("value", "turnover", "totalvalue"))

            if None in (open_price, high, low, close, volume):
                invalid_rows += 1
                continue
            assert open_price is not None
            assert high is not None
            assert low is not None
            assert close is not None
            assert volume is not None
            if (
                open_price <= 0
                or high <= 0
                or low <= 0
                or close <= 0
                or volume < 0
                or high < low
                or not (low <= open_price <= high)
                or not (low <= close <= high)
            ):
                invalid_rows += 1
                continue

            normalized[symbol] = OhlcRow(
                symbol=symbol,
                trade_date=trade_date,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                trade=trade,
                value=value,
            )

        if not normalized:
            raise CollectorSourceError("DSE source returned no valid rows inside the approved OHLC universe.")

        missing = sorted(allowed_symbols - set(normalized))
        warnings: list[str] = []
        if invalid_rows:
            warnings.append(f"{invalid_rows} source rows failed OHLC validation and were not saved.")
        if outside_universe:
            warnings.append(f"{outside_universe} non-universe instruments were ignored.")
        if wrong_date_rows:
            warnings.append(f"{wrong_date_rows} rows outside the requested trade date were ignored.")
        if missing:
            warnings.append(f"{len(missing)} approved symbols were absent from the source response.")

        return CollectorBatch(
            rows=list(normalized.values()),
            fetched_rows=len(raw_records),
            invalid_rows=invalid_rows,
            missing_symbols=missing,
            warnings=warnings,
        )


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _first_value(item: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in item:
            return item[alias]
    return None


def _first_text(item: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
    value = _first_value(item, aliases)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-", "--"}:
        return None
    return text


def _first_float(item: dict[str, Any], aliases: tuple[str, ...]) -> float | None:
    value = _first_value(item, aliases)
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).replace(",", "").strip()
    if not text or text.lower() in {"nan", "none", "-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_int(item: dict[str, Any], aliases: tuple[str, ...]) -> int | None:
    value = _first_float(item, aliases)
    if value is None:
        return None
    return int(value)


def _first_date(item: dict[str, Any], aliases: tuple[str, ...]) -> date | None:
    value = _first_value(item, aliases)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    date_method = getattr(value, "date", None)
    if callable(date_method):
        try:
            result = date_method()
            if isinstance(result, date):
                return result
        except (TypeError, ValueError):
            pass
    text = str(value).strip().split(" ", maxsplit=1)[0]
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None
