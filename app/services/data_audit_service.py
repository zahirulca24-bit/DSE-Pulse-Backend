"""Database-backed DSE OHLC integrity audit service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import OhlcDaily
from app.schemas.data import DataAuditResponse


class DataAuditService:
    """Calculate transparent data-quality metrics from stored OHLC rows."""

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager

    def audit(self) -> DataAuditResponse:
        audited_at = datetime.now(timezone.utc)
        if not self._manager.has_tables(("ohlc_daily",)):
            return self._empty("Database OHLC table is unavailable.", audited_at)

        try:
            with self._manager.session() as session:
                rows_count, symbols_count, earliest, latest = session.execute(
                    select(
                        func.count(OhlcDaily.id),
                        func.count(func.distinct(OhlcDaily.symbol)),
                        func.min(OhlcDaily.trade_date),
                        func.max(OhlcDaily.trade_date),
                    )
                ).one()

                duplicate_groups = (
                    select(OhlcDaily.symbol, OhlcDaily.trade_date)
                    .group_by(OhlcDaily.symbol, OhlcDaily.trade_date)
                    .having(func.count(OhlcDaily.id) > 1)
                    .subquery()
                )
                duplicate_rows = session.scalar(select(func.count()).select_from(duplicate_groups)) or 0

                zero_volume_rows = session.scalar(
                    select(func.count(OhlcDaily.id)).where(OhlcDaily.volume <= 0)
                ) or 0

                non_positive_price_rows = session.scalar(
                    select(func.count(OhlcDaily.id)).where(
                        or_(
                            OhlcDaily.open <= 0,
                            OhlcDaily.high <= 0,
                            OhlcDaily.low <= 0,
                            OhlcDaily.close <= 0,
                        )
                    )
                ) or 0

                invalid_ohlc_rows = session.scalar(
                    select(func.count(OhlcDaily.id)).where(
                        or_(
                            OhlcDaily.high < OhlcDaily.low,
                            OhlcDaily.open < OhlcDaily.low,
                            OhlcDaily.open > OhlcDaily.high,
                            OhlcDaily.close < OhlcDaily.low,
                            OhlcDaily.close > OhlcDaily.high,
                        )
                    )
                ) or 0

                symbol_counts = (
                    select(
                        OhlcDaily.symbol.label("symbol"),
                        func.count(OhlcDaily.id).label("row_count"),
                    )
                    .group_by(OhlcDaily.symbol)
                    .subquery()
                )
                insufficient_history = session.scalar(
                    select(func.count()).select_from(symbol_counts).where(symbol_counts.c.row_count < 60)
                ) or 0

                latest_date_symbols = 0
                if latest is not None:
                    latest_date_symbols = session.scalar(
                        select(func.count(func.distinct(OhlcDaily.symbol))).where(OhlcDaily.trade_date == latest)
                    ) or 0
        except (SQLAlchemyError, RuntimeError):
            return self._empty("Database OHLC audit could not be completed.", audited_at)

        rows = int(rows_count or 0)
        symbols = int(symbols_count or 0)
        latest_symbols = int(latest_date_symbols)
        stale_symbols = max(symbols - latest_symbols, 0)
        latest_coverage = round((latest_symbols / symbols) * 100, 2) if symbols else 0.0

        warnings: list[str] = []
        if duplicate_rows:
            warnings.append(f"{int(duplicate_rows)} duplicate symbol/date groups detected.")
        if zero_volume_rows:
            warnings.append(f"{int(zero_volume_rows)} rows have zero or negative volume.")
        if non_positive_price_rows:
            warnings.append(f"{int(non_positive_price_rows)} rows have non-positive OHLC prices.")
        if invalid_ohlc_rows:
            warnings.append(f"{int(invalid_ohlc_rows)} rows violate OHLC range consistency.")
        if insufficient_history:
            warnings.append(f"{int(insufficient_history)} symbols have fewer than 60 rows and will be scanner-ineligible.")
        if stale_symbols:
            warnings.append(
                f"{stale_symbols} symbols do not have a row on the dataset latest trade date; review suspensions or data gaps."
            )
        if not warnings and rows:
            warnings.append("No core OHLC integrity issues were detected.")

        scanner_ready = (
            rows > 0
            and symbols > 0
            and int(duplicate_rows) == 0
            and int(non_positive_price_rows) == 0
            and int(invalid_ohlc_rows) == 0
        )

        return DataAuditResponse(
            ok=rows > 0,
            data_source="database" if rows > 0 else "none",
            rows_count=rows,
            symbols_count=symbols,
            earliest_trade_date=earliest,
            latest_trade_date=latest,
            duplicate_symbol_date_rows=int(duplicate_rows),
            zero_volume_rows=int(zero_volume_rows),
            non_positive_price_rows=int(non_positive_price_rows),
            invalid_ohlc_rows=int(invalid_ohlc_rows),
            symbols_with_fewer_than_60_rows=int(insufficient_history),
            latest_date_symbols_count=latest_symbols,
            latest_date_coverage_percent=latest_coverage,
            stale_symbols_count=stale_symbols,
            scanner_ready=scanner_ready,
            warnings=warnings,
            audited_at=audited_at,
        )

    @staticmethod
    def _empty(message: str, audited_at: datetime) -> DataAuditResponse:
        return DataAuditResponse(
            ok=False,
            data_source="none",
            rows_count=0,
            symbols_count=0,
            earliest_trade_date=None,
            latest_trade_date=None,
            duplicate_symbol_date_rows=0,
            zero_volume_rows=0,
            non_positive_price_rows=0,
            invalid_ohlc_rows=0,
            symbols_with_fewer_than_60_rows=0,
            latest_date_symbols_count=0,
            latest_date_coverage_percent=0.0,
            stale_symbols_count=0,
            scanner_ready=False,
            warnings=[message],
            audited_at=audited_at,
        )
