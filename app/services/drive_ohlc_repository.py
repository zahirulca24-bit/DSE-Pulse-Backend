"""Google Drive backed OHLC repository with local cache for fast reads."""

from __future__ import annotations

import csv
import io
from datetime import date

from app.schemas.ohlc import OhlcResponse, OhlcRow, SymbolsResponse
from app.services.csv_ingestion_service import (
    NORMALIZED_HEADERS,
    CsvIngestionService,
    CsvParseResult,
)
from app.services.google_drive_client import GoogleDriveClient, GoogleDriveStatus
from app.services.ohlc_repository import OhlcRepository


class DriveOhlcRepository(OhlcRepository):
    """Persist the canonical master CSV in Drive and keep a local read cache."""

    def __init__(
        self,
        local_repository: OhlcRepository,
        drive_client: GoogleDriveClient,
        master_filename: str,
        ingestion_service: CsvIngestionService | None = None,
    ) -> None:
        super().__init__(local_repository.storage_path, ingestion_service)
        self._drive_client = drive_client
        self._master_filename = master_filename.strip() or "DSE_OHLC_MASTER.csv"
        self._sync_attempted = False

    @property
    def master_filename(self) -> str:
        return self._master_filename

    def drive_status(self) -> GoogleDriveStatus:
        return self._drive_client.status()

    def sync_from_drive(self, force: bool = False) -> bool:
        """Download the canonical Drive master into the local cache when needed."""

        if not force and self.storage_path.is_file():
            self._sync_attempted = True
            return True
        if self._sync_attempted and not force:
            return self.storage_path.is_file()
        self._sync_attempted = True
        if not self._drive_client.configured:
            return self.storage_path.is_file()
        content = self._drive_client.download_by_name(self._master_filename)
        if content is None:
            return self.storage_path.is_file()
        result = self._ingestion_service.parse_bytes(content, self._master_filename)
        if not result.ok:
            return False
        super().save(result)
        return True

    def merge_and_save_to_drive(
        self,
        uploaded: CsvParseResult,
    ) -> tuple[int, int, CsvParseResult]:
        """Upsert uploaded rows by symbol/date, replace Drive master, then refresh local cache."""

        status = self._drive_client.status()
        if not status.connected:
            raise RuntimeError(status.message)
        self.sync_from_drive()
        existing = super().read_result()
        existing_rows = [] if existing is None or not existing.ok else existing.valid_rows
        existing_by_key = {
            (row.symbol.upper(), row.trade_date): row
            for row in existing_rows
        }
        uploaded_by_key = {
            (row.symbol.upper(), row.trade_date): row
            for row in uploaded.valid_rows
        }
        updated = sum(key in existing_by_key for key in uploaded_by_key)
        inserted = len(uploaded_by_key) - updated
        merged_by_key = dict(existing_by_key)
        merged_by_key.update(uploaded_by_key)
        merged_rows = sorted(
            merged_by_key.values(),
            key=lambda row: (row.symbol.upper(), row.trade_date),
        )
        merged = CsvParseResult(
            filename=self._master_filename,
            detected_headers=list(NORMALIZED_HEADERS),
            valid_rows=merged_rows,
            invalid_rows=0,
            warnings=[],
            errors=[],
        )
        payload = self._serialize_rows(merged_rows)
        self._drive_client.upload_or_replace(
            self._master_filename,
            payload,
            "text/csv",
        )
        super().save(merged)
        self._sync_attempted = True
        return inserted, updated, merged

    def read_result(self) -> CsvParseResult | None:
        self.sync_from_drive()
        return super().read_result()

    def get_all_rows(self) -> list[OhlcRow]:
        result = self.read_result()
        return [] if result is None or not result.ok else result.valid_rows

    def get_symbols(self) -> SymbolsResponse:
        return super().get_symbols()

    def get_ohlc(
        self,
        symbol: str,
        limit: int,
        start_date: date | None,
        end_date: date | None,
    ) -> OhlcResponse:
        return super().get_ohlc(symbol, limit, start_date, end_date)

    @staticmethod
    def _serialize_rows(rows: list[OhlcRow]) -> bytes:
        handle = io.StringIO(newline="")
        writer = csv.DictWriter(handle, fieldnames=list(NORMALIZED_HEADERS))
        writer.writeheader()
        for row in rows:
            writer.writerow(OhlcRepository._row_to_csv(row))
        return handle.getvalue().encode("utf-8")
