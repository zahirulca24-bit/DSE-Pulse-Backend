"""Standard-library CSV validation and normalization for local DSE OHLC data."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.schemas.ohlc import OhlcRow

NORMALIZED_HEADERS: tuple[str, ...] = (
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade",
    "value",
)
_REQUIRED_BASE_HEADERS = {"symbol", "open", "high", "low", "close", "volume"}
_OPTIONAL_HEADERS = ("trade", "value")
_MAX_DETAIL_ERRORS = 100


@dataclass(slots=True)
class CsvParseResult:
    """Internal complete parse result used by preview, import, and repository reads."""

    filename: str
    detected_headers: list[str]
    valid_rows: list[OhlcRow]
    invalid_rows: int
    warnings: list[str]
    errors: list[str]
    fatal_error: bool = False

    @property
    def ok(self) -> bool:
        return not self.fatal_error and bool(self.valid_rows)

    @property
    def symbols_count(self) -> int:
        return len({row.symbol for row in self.valid_rows})

    @property
    def latest_trade_date(self) -> date | None:
        return max((row.trade_date for row in self.valid_rows), default=None)

    @property
    def earliest_trade_date(self) -> date | None:
        return min((row.trade_date for row in self.valid_rows), default=None)


class CsvIngestionService:
    """Parse uploaded or stored CSV content without external dependencies."""

    def parse_bytes(self, content: bytes, filename: str) -> CsvParseResult:
        """Decode, validate, and normalize uploaded CSV bytes."""

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return CsvParseResult(
                filename=filename,
                detected_headers=[],
                valid_rows=[],
                invalid_rows=0,
                warnings=[],
                errors=["Unreadable CSV file: UTF-8 encoding is required."],
                fatal_error=True,
            )
        return self.parse_text(text, filename)

    def parse_path(self, path: Path) -> CsvParseResult:
        """Read and parse a CSV path, returning a clear fatal result on I/O failure."""

        try:
            content = path.read_bytes()
        except OSError as exc:
            return CsvParseResult(
                filename=path.name,
                detected_headers=[],
                valid_rows=[],
                invalid_rows=0,
                warnings=[],
                errors=[f"Unreadable CSV file: {exc}."],
                fatal_error=True,
            )
        return self.parse_bytes(content, path.name)

    def parse_text(self, text: str, filename: str) -> CsvParseResult:
        """Validate headers and rows, returning only normalized valid records."""

        try:
            reader = csv.DictReader(io.StringIO(text, newline=""))
            raw_headers = reader.fieldnames
        except csv.Error as exc:
            return self._fatal(filename, [], f"Unreadable CSV file: {exc}.")

        if raw_headers is None:
            return self._fatal(filename, [], "Missing CSV header row.")

        detected_headers = [header.strip().lower() for header in raw_headers]
        if any(not header for header in detected_headers):
            return self._fatal(filename, detected_headers, "CSV contains an empty header name.")
        if len(set(detected_headers)) != len(detected_headers):
            return self._fatal(filename, detected_headers, "CSV contains duplicate header names.")

        reader.fieldnames = detected_headers
        missing = sorted(_REQUIRED_BASE_HEADERS - set(detected_headers))
        if "trade_date" not in detected_headers and "date" not in detected_headers:
            missing.append("trade_date (or date)")
        if missing:
            return self._fatal(
                filename,
                detected_headers,
                "Missing required columns: " + ", ".join(missing) + ".",
            )

        warnings = [
            f"Optional column '{header}' is missing; values are normalized to null."
            for header in _OPTIONAL_HEADERS
            if header not in detected_headers
        ]
        if "trade_date" in detected_headers and "date" in detected_headers:
            warnings.append("Both 'trade_date' and 'date' were provided; 'trade_date' was used.")

        valid_rows: list[OhlcRow] = []
        errors: list[str] = []
        invalid_rows = 0
        duplicate_rows = 0
        zero_volume_rows = 0
        seen_keys: set[tuple[str, date]] = set()

        try:
            for row_number, raw_row in enumerate(reader, start=2):
                if self._is_blank_row(raw_row):
                    continue
                try:
                    normalized = self._normalize_row(raw_row)
                except ValueError as exc:
                    invalid_rows += 1
                    if len(errors) < _MAX_DETAIL_ERRORS:
                        errors.append(f"Row {row_number}: {exc}")
                    continue

                key = (normalized.symbol, normalized.trade_date)
                if key in seen_keys:
                    duplicate_rows += 1
                seen_keys.add(key)
                if normalized.volume == 0:
                    zero_volume_rows += 1
                valid_rows.append(normalized)
        except csv.Error as exc:
            return self._fatal(filename, detected_headers, f"Unreadable CSV file: {exc}.")

        if invalid_rows:
            warnings.append(f"{invalid_rows} invalid row(s) were skipped.")
        if invalid_rows > len(errors):
            warnings.append(
                f"Only the first {_MAX_DETAIL_ERRORS} row validation errors are listed."
            )
        if duplicate_rows:
            warnings.append(
                f"Duplicate symbol/trade_date rows detected: {duplicate_rows}."
            )
        if zero_volume_rows:
            warnings.append(f"Zero volume rows detected: {zero_volume_rows}.")
        if not valid_rows:
            errors.append("No valid rows found.")
            return CsvParseResult(
                filename=filename,
                detected_headers=detected_headers,
                valid_rows=[],
                invalid_rows=invalid_rows,
                warnings=warnings,
                errors=errors,
                fatal_error=True,
            )

        return CsvParseResult(
            filename=filename,
            detected_headers=detected_headers,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def _fatal(filename: str, headers: list[str], error: str) -> CsvParseResult:
        return CsvParseResult(
            filename=filename,
            detected_headers=headers,
            valid_rows=[],
            invalid_rows=0,
            warnings=[],
            errors=[error],
            fatal_error=True,
        )

    @staticmethod
    def _is_blank_row(row: dict[str, Any]) -> bool:
        return all(value is None or str(value).strip() == "" for value in row.values())

    def _normalize_row(self, row: dict[str, Any]) -> OhlcRow:
        symbol = self._text(row.get("symbol")).upper()
        if not symbol:
            raise ValueError("symbol is required.")

        raw_date = self._text(row.get("trade_date")) or self._text(row.get("date"))
        trade_date = self._parse_date(raw_date)

        open_price = self._parse_decimal(row.get("open"), "open")
        high_price = self._parse_decimal(row.get("high"), "high")
        low_price = self._parse_decimal(row.get("low"), "low")
        close_price = self._parse_decimal(row.get("close"), "close")
        for name, price_value in (
            ("open", open_price),
            ("high", high_price),
            ("low", low_price),
            ("close", close_price),
        ):
            if price_value < 0:
                raise ValueError(f"{name} must not be negative.")
        if high_price < low_price:
            raise ValueError("high must not be lower than low.")

        volume_decimal = self._parse_decimal(row.get("volume"), "volume")
        if volume_decimal < 0:
            raise ValueError("volume must not be negative.")
        if volume_decimal != volume_decimal.to_integral_value():
            raise ValueError("volume must be integer-compatible.")

        trade = self._parse_optional_decimal(row.get("trade"), "trade")
        value = self._parse_optional_decimal(row.get("value"), "value")

        return OhlcRow(
            symbol=symbol,
            trade_date=trade_date,
            open=float(open_price),
            high=float(high_price),
            low=float(low_price),
            close=float(close_price),
            volume=int(volume_decimal),
            trade=float(trade) if trade is not None else None,
            value=float(value) if value is not None else None,
        )

    @staticmethod
    def _text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @classmethod
    def _parse_date(cls, value: str) -> date:
        if not value:
            raise ValueError("trade_date is required.")
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("trade_date must use YYYY-MM-DD format.") from exc
        if parsed.isoformat() != value:
            raise ValueError("trade_date must use YYYY-MM-DD format.")
        return parsed

    @classmethod
    def _parse_decimal(cls, value: Any, field: str) -> Decimal:
        text = cls._text(value)
        if not text:
            raise ValueError(f"{field} is required.")
        try:
            parsed = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{field} must be numeric.") from exc
        if not parsed.is_finite():
            raise ValueError(f"{field} must be a finite number.")
        return parsed

    @classmethod
    def _parse_optional_decimal(cls, value: Any, field: str) -> Decimal | None:
        text = cls._text(value)
        if not text:
            return None
        return cls._parse_decimal(text, field)
