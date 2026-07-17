"""Local normalized CSV storage and read repository."""

import csv
import os
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.data import DataStatusResponse
from app.schemas.ohlc import OhlcResponse, OhlcRow, SymbolsResponse
from app.services.csv_ingestion_service import (
    NORMALIZED_HEADERS,
    CsvIngestionService,
    CsvParseResult,
)


class OhlcRepository:
    def __init__(self, storage_path: Path, ingestion_service: CsvIngestionService | None = None) -> None:
        self.storage_path = storage_path
        self._ingestion_service = ingestion_service or CsvIngestionService()

    @property
    def stored_path(self) -> str:
        return self.storage_path.as_posix()

    def save(self, result: CsvParseResult) -> None:
        if not result.valid_rows:
            raise ValueError("Cannot save a CSV import with no valid rows.")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=self.storage_path.parent,
                                    prefix=f".{self.storage_path.name}.", suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                writer = csv.DictWriter(handle, fieldnames=list(NORMALIZED_HEADERS))
                writer.writeheader()
                for row in result.valid_rows:
                    writer.writerow(self._row_to_csv(row))
            os.replace(temp_path, self.storage_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def read_result(self) -> CsvParseResult | None:
        if not self.storage_path.is_file():
            return None
        return self._ingestion_service.parse_path(self.storage_path)

    def get_all_rows(self) -> list[OhlcRow]:
        result = self.read_result()
        return [] if result is None or not result.ok else result.valid_rows

    def get_status(self) -> DataStatusResponse:
        result = self.read_result()
        if result is None:
            return DataStatusResponse(data_available=False, data_source="none", stored_path=None,
                symbols_count=None, rows_count=None, latest_trade_date=None, earliest_trade_date=None,
                message="No local DSE OHLC CSV has been imported yet.")
        if not result.ok:
            return DataStatusResponse(data_available=False, data_source="none", stored_path=self.stored_path,
                symbols_count=None, rows_count=None, latest_trade_date=None, earliest_trade_date=None,
                message="The local DSE OHLC CSV contains no readable valid rows.")
        return DataStatusResponse(data_available=True, data_source="local_csv", stored_path=self.stored_path,
            symbols_count=result.symbols_count, rows_count=len(result.valid_rows),
            latest_trade_date=result.latest_trade_date, earliest_trade_date=result.earliest_trade_date,
            message="Local DSE OHLC CSV is available.")

    def get_symbols(self) -> SymbolsResponse:
        result = self.read_result()
        if result is None or not result.ok:
            return SymbolsResponse(data_source="none", symbols_count=0, symbols=[])
        symbols = sorted({row.symbol for row in result.valid_rows})
        return SymbolsResponse(data_source="local_csv", symbols_count=len(symbols), symbols=symbols)

    def get_ohlc(self, symbol: str, limit: int, start_date: date | None, end_date: date | None) -> OhlcResponse:
        normalized = symbol.strip().upper()
        result = self.read_result()
        if result is None or not result.ok:
            return OhlcResponse(symbol=normalized, data_source="none", rows_count=0, rows=[])
        rows = [row for row in result.valid_rows if row.symbol == normalized
                and (start_date is None or row.trade_date >= start_date)
                and (end_date is None or row.trade_date <= end_date)]
        rows.sort(key=lambda row: row.trade_date, reverse=True)
        rows = rows[:limit]
        return OhlcResponse(symbol=normalized, data_source="local_csv", rows_count=len(rows), rows=rows)

    @staticmethod
    def _row_to_csv(row: OhlcRow) -> dict[str, str]:
        return {"symbol": row.symbol, "trade_date": row.trade_date.isoformat(),
            "open": OhlcRepository._format_number(row.open), "high": OhlcRepository._format_number(row.high),
            "low": OhlcRepository._format_number(row.low), "close": OhlcRepository._format_number(row.close),
            "volume": str(row.volume), "trade": "" if row.trade is None else OhlcRepository._format_number(row.trade),
            "value": "" if row.value is None else OhlcRepository._format_number(row.value)}

    @staticmethod
    def _format_number(value: float) -> str:
        return format(value, ".15g")
