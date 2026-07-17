"""SQLAlchemy repository for optional database-backed OHLC storage."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import OhlcDaily
from app.schemas.data import DataStatusResponse
from app.schemas.ohlc import OhlcResponse, OhlcRow, SymbolsResponse

_BATCH_SIZE = 1000
_T = TypeVar("_T")


class OhlcDbRepository:
    """Read and upsert OHLC rows when the optional database is available."""

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager

    def is_available(self) -> bool:
        return self._manager.has_tables(("ohlc_daily",))

    def upsert(self, rows: list[OhlcRow]) -> tuple[int, int]:
        """Upsert by symbol/trade_date and return inserted and updated counts."""

        if not rows or not self.is_available():
            return (0, 0)
        unique_rows = list({(row.symbol.upper(), row.trade_date): row for row in rows}.values())
        keys = [(row.symbol.upper(), row.trade_date) for row in unique_rows]
        existing: set[tuple[str, date]] = set()
        try:
            with self._manager.session() as session:
                for batch in self._chunks(keys):
                    existing.update(
                        (symbol, trade_date)
                        for symbol, trade_date in session.execute(
                            select(OhlcDaily.symbol, OhlcDaily.trade_date).where(
                                tuple_(OhlcDaily.symbol, OhlcDaily.trade_date).in_(batch)
                            )
                        ).all()
                    )
                dialect = session.get_bind().dialect.name
                for batch_rows in self._chunks(unique_rows):
                    values = [self._values(row) for row in batch_rows]
                    if dialect == "postgresql":
                        statement = postgresql_insert(OhlcDaily).values(values)
                        statement = statement.on_conflict_do_update(
                            index_elements=[OhlcDaily.symbol, OhlcDaily.trade_date],
                            set_={
                                "open": statement.excluded.open,
                                "high": statement.excluded.high,
                                "low": statement.excluded.low,
                                "close": statement.excluded.close,
                                "volume": statement.excluded.volume,
                                "trade": statement.excluded.trade,
                                "value": statement.excluded.value,
                                "updated_at": func.now(),
                            },
                        )
                        session.execute(statement)
                    elif dialect == "sqlite":
                        sqlite_statement = sqlite_insert(OhlcDaily).values(values)
                        sqlite_statement = sqlite_statement.on_conflict_do_update(
                            index_elements=["symbol", "trade_date"],
                            set_={
                                "open": sqlite_statement.excluded.open,
                                "high": sqlite_statement.excluded.high,
                                "low": sqlite_statement.excluded.low,
                                "close": sqlite_statement.excluded.close,
                                "volume": sqlite_statement.excluded.volume,
                                "trade": sqlite_statement.excluded.trade,
                                "value": sqlite_statement.excluded.value,
                                "updated_at": func.now(),
                            },
                        )
                        session.execute(sqlite_statement)
                    else:
                        for row in batch_rows:
                            current = session.scalar(
                                select(OhlcDaily).where(
                                    OhlcDaily.symbol == row.symbol.upper(),
                                    OhlcDaily.trade_date == row.trade_date,
                                )
                            )
                            if current is None:
                                session.add(OhlcDaily(**self._values(row)))
                            else:
                                self._apply(current, row)
                session.commit()
        except (SQLAlchemyError, RuntimeError):
            return (0, 0)
        updated = sum(key in existing for key in keys)
        return (len(unique_rows) - updated, updated)

    def get_status(self) -> DataStatusResponse:
        if not self.is_available():
            return self._empty_status("Database OHLC storage is unavailable.")
        try:
            with self._manager.session() as session:
                rows_count, symbols_count, latest, earliest = session.execute(
                    select(
                        func.count(OhlcDaily.id),
                        func.count(func.distinct(OhlcDaily.symbol)),
                        func.max(OhlcDaily.trade_date),
                        func.min(OhlcDaily.trade_date),
                    )
                ).one()
        except (SQLAlchemyError, RuntimeError):
            return self._empty_status("Database OHLC storage is unavailable.")
        return DataStatusResponse(
            data_available=bool(rows_count),
            data_source="database",
            stored_path=None,
            symbols_count=int(symbols_count),
            rows_count=int(rows_count),
            latest_trade_date=latest,
            earliest_trade_date=earliest,
            message=(
                "Database DSE OHLC data is available."
                if rows_count
                else "Database OHLC table is available but contains no rows."
            ),
        )

    def get_symbols(self) -> SymbolsResponse:
        if not self.is_available():
            return SymbolsResponse(data_source="none", symbols_count=0, symbols=[])
        try:
            with self._manager.session() as session:
                symbols = list(
                    session.scalars(select(OhlcDaily.symbol).distinct().order_by(OhlcDaily.symbol)).all()
                )
        except (SQLAlchemyError, RuntimeError):
            return SymbolsResponse(data_source="none", symbols_count=0, symbols=[])
        return SymbolsResponse(data_source="database", symbols_count=len(symbols), symbols=symbols)

    def get_ohlc(
        self,
        symbol: str,
        limit: int,
        start_date: date | None,
        end_date: date | None,
    ) -> OhlcResponse:
        normalized = symbol.strip().upper()
        if not self.is_available():
            return OhlcResponse(symbol=normalized, data_source="none", rows_count=0, rows=[])
        statement = select(OhlcDaily).where(OhlcDaily.symbol == normalized)
        if start_date is not None:
            statement = statement.where(OhlcDaily.trade_date >= start_date)
        if end_date is not None:
            statement = statement.where(OhlcDaily.trade_date <= end_date)
        statement = statement.order_by(OhlcDaily.trade_date.desc()).limit(limit)
        try:
            with self._manager.session() as session:
                records = list(session.scalars(statement).all())
        except (SQLAlchemyError, RuntimeError):
            return OhlcResponse(symbol=normalized, data_source="none", rows_count=0, rows=[])
        rows = [self._to_schema(record) for record in records]
        return OhlcResponse(symbol=normalized, data_source="database", rows_count=len(rows), rows=rows)

    def get_all_rows(self) -> list[OhlcRow]:
        if not self.is_available():
            return []
        try:
            with self._manager.session() as session:
                records = list(
                    session.scalars(select(OhlcDaily).order_by(OhlcDaily.symbol, OhlcDaily.trade_date)).all()
                )
        except (SQLAlchemyError, RuntimeError):
            return []
        return [self._to_schema(record) for record in records]

    @staticmethod
    def _chunks(values: Sequence[_T], size: int = _BATCH_SIZE) -> Iterator[list[_T]]:
        for start in range(0, len(values), size):
            yield list(values[start : start + size])

    @staticmethod
    def _values(row: OhlcRow) -> dict[str, object]:
        return {
            "symbol": row.symbol.upper(),
            "trade_date": row.trade_date,
            "open": Decimal(str(row.open)),
            "high": Decimal(str(row.high)),
            "low": Decimal(str(row.low)),
            "close": Decimal(str(row.close)),
            "volume": row.volume,
            "trade": None if row.trade is None else Decimal(str(row.trade)),
            "value": None if row.value is None else Decimal(str(row.value)),
        }

    @staticmethod
    def _apply(record: OhlcDaily, row: OhlcRow) -> None:
        values = OhlcDbRepository._values(row)
        record.open = values["open"]  # type: ignore[assignment]
        record.high = values["high"]  # type: ignore[assignment]
        record.low = values["low"]  # type: ignore[assignment]
        record.close = values["close"]  # type: ignore[assignment]
        record.volume = row.volume
        record.trade = values["trade"]  # type: ignore[assignment]
        record.value = values["value"]  # type: ignore[assignment]

    @staticmethod
    def _to_schema(record: OhlcDaily) -> OhlcRow:
        return OhlcRow(
            symbol=record.symbol,
            trade_date=record.trade_date,
            open=float(record.open),
            high=float(record.high),
            low=float(record.low),
            close=float(record.close),
            volume=record.volume,
            trade=None if record.trade is None else float(record.trade),
            value=None if record.value is None else float(record.value),
        )

    @staticmethod
    def _empty_status(message: str) -> DataStatusResponse:
        return DataStatusResponse(
            data_available=False,
            data_source="none",
            stored_path=None,
            symbols_count=None,
            rows_count=None,
            latest_trade_date=None,
            earliest_trade_date=None,
            message=message,
        )
