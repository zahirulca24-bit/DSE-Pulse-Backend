"""Regression tests for row-backed source consistency across read routes."""

from datetime import date
from types import SimpleNamespace

from app.api.routes.ohlc import get_symbol_ohlc
from app.api.routes.symbols import get_symbols
from app.schemas.ohlc import OhlcResponse, OhlcRow, SymbolsResponse


class _EmptyDatabaseRepository:
    def get_status(self) -> SimpleNamespace:
        return SimpleNamespace(data_available=False)

    def is_available(self) -> bool:
        return True

    def get_symbols(self) -> SymbolsResponse:
        raise AssertionError("Empty database must not serve auto symbols.")

    def get_ohlc(self, *args: object) -> OhlcResponse:
        raise AssertionError("Empty database must not serve auto OHLC.")


class _ReadyDatabaseRepository(_EmptyDatabaseRepository):
    def get_status(self) -> SimpleNamespace:
        return SimpleNamespace(data_available=True)

    def get_symbols(self) -> SymbolsResponse:
        return SymbolsResponse(
            data_source="database",
            symbols_count=1,
            symbols=["GP"],
        )

    def get_ohlc(self, *args: object) -> OhlcResponse:
        return OhlcResponse(
            symbol="GP",
            data_source="database",
            rows_count=1,
            rows=[
                OhlcRow(
                    symbol="GP",
                    trade_date=date(2026, 7, 30),
                    open=280,
                    high=286,
                    low=278,
                    close=284.5,
                    volume=510000,
                )
            ],
        )


class _LocalRepository:
    def get_symbols(self) -> SymbolsResponse:
        return SymbolsResponse(
            data_source="local_csv",
            symbols_count=1,
            symbols=["BATBC"],
        )

    def get_ohlc(self, *args: object) -> OhlcResponse:
        return OhlcResponse(
            symbol="BATBC",
            data_source="local_csv",
            rows_count=1,
            rows=[
                OhlcRow(
                    symbol="BATBC",
                    trade_date=date(2026, 7, 30),
                    open=420,
                    high=425,
                    low=418,
                    close=423,
                    volume=100000,
                )
            ],
        )


def test_symbols_fall_back_to_local_when_database_has_no_rows() -> None:
    response = get_symbols(_EmptyDatabaseRepository(), _LocalRepository())

    assert response.data_source == "local_csv"
    assert response.symbols == ["BATBC"]


def test_auto_ohlc_falls_back_to_local_when_database_has_no_rows() -> None:
    response = get_symbol_ohlc(
        "BATBC",
        _EmptyDatabaseRepository(),
        _LocalRepository(),
        source="auto",
    )

    assert response.data_source == "local_csv"
    assert response.rows[0].symbol == "BATBC"


def test_ready_database_remains_primary_for_read_routes() -> None:
    database = _ReadyDatabaseRepository()
    local = _LocalRepository()

    symbols = get_symbols(database, local)
    ohlc = get_symbol_ohlc("GP", database, local, source="auto")

    assert symbols.data_source == "database"
    assert ohlc.data_source == "database"
