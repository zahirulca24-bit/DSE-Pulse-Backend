"""Atomic local persistence for market scanner scheduler slot state."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock

from pydantic import BaseModel, ConfigDict, ValidationError


class ScannerSchedulerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_slot: str | None = None
    last_started_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_result_ok: bool | None = None
    last_message: str | None = None


class ScannerSchedulerStateRepository:
    """Persist the last claimed schedule slot so process restarts do not duplicate it."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = RLock()

    def load(self) -> ScannerSchedulerState:
        if not self.storage_path.is_file():
            return ScannerSchedulerState()
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return ScannerSchedulerState.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError, TypeError):
            return ScannerSchedulerState()

    def claim(self, slot: str) -> bool:
        with self._lock:
            state = self.load()
            if state.last_slot == slot:
                return False
            self._write(
                state.model_copy(
                    update={
                        "last_slot": slot,
                        "last_started_at": datetime.now(UTC),
                        "last_completed_at": None,
                        "last_result_ok": None,
                        "last_message": None,
                    }
                )
            )
            return True

    def complete(self, *, ok: bool, message: str) -> None:
        with self._lock:
            state = self.load()
            self._write(
                state.model_copy(
                    update={
                        "last_completed_at": datetime.now(UTC),
                        "last_result_ok": ok,
                        "last_message": message[:1000],
                    }
                )
            )

    def _write(self, state: ScannerSchedulerState) -> None:
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
                json.dump(state.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_path, self.storage_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
