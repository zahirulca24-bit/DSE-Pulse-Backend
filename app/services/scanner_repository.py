"""Atomic local JSON persistence for the latest scanner result."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import ValidationError

from app.schemas.scanner_result import ScannerResultResponse


class ScannerRepository:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path

    def save(self, result: ScannerResultResponse) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.storage_path.parent,
                prefix=f".{self.storage_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(result.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_path, self.storage_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def clear(self) -> None:
        """Remove the latest result after a successful OHLC dataset replacement."""

        try:
            self.storage_path.unlink()
        except FileNotFoundError:
            return

    def load(self) -> ScannerResultResponse | None:
        if not self.storage_path.is_file():
            return None
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return ScannerResultResponse.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None
