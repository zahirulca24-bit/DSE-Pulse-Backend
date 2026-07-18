"""Google Drive storage API schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DriveStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    connected: bool
    storage_type: Literal["google_drive"]
    folder_name: str | None
    master_filename: str
    message: str


class DriveImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    data_source: Literal["google_drive"]
    inserted_rows: int
    updated_rows: int
    invalid_rows: int
    symbols_count: int
    rows_count: int
    earliest_trade_date: date | None
    latest_trade_date: date | None
    master_filename: str
    message: str
