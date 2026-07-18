"""Atomic local JSON persistence for collector job state without a database."""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.collector import CollectorRunResponse

_MAX_HISTORY = 100


class CollectorJobRepository:
    """Persist collector job state locally so the production collector needs no DB."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = RLock()

    def is_available(self) -> bool:
        return True

    def create(self, trade_date: date, source: str) -> CollectorRunResponse:
        job = CollectorRunResponse(
            job_id=str(uuid4()),
            status="queued",
            requested_trade_date=trade_date,
            source=source,
            fetched_rows=0,
            collected_symbols=0,
            inserted_rows=0,
            updated_rows=0,
            invalid_rows=0,
            missing_symbols=[],
            warnings=[],
            error_message=None,
            scanner_refresh_required=False,
            created_at=datetime.now(UTC),
            started_at=None,
            completed_at=None,
        )
        with self._lock:
            jobs = self._read()
            jobs.append(job)
            self._write(jobs[-_MAX_HISTORY:])
        return job

    def fail_stale_active(self, max_age_minutes: int = 30) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        failed = 0
        with self._lock:
            jobs = self._read()
            updated: list[CollectorRunResponse] = []
            for job in jobs:
                reference = job.started_at or job.created_at
                if job.status in {"queued", "running"} and reference < cutoff:
                    job = job.model_copy(
                        update={
                            "status": "failed",
                            "error_message": "Collector job expired before completion; start a new manual run.",
                            "scanner_refresh_required": False,
                            "completed_at": datetime.now(UTC),
                        }
                    )
                    failed += 1
                updated.append(job)
            if failed:
                self._write(updated)
        return failed

    def get_active(self) -> CollectorRunResponse | None:
        active = [job for job in self._read() if job.status in {"queued", "running"}]
        return active[-1] if active else None

    def get(self, job_id: str) -> CollectorRunResponse | None:
        return next((job for job in reversed(self._read()) if job.job_id == job_id), None)

    def latest(self) -> CollectorRunResponse | None:
        jobs = self._read()
        return jobs[-1] if jobs else None

    def history(self, limit: int = 20) -> list[CollectorRunResponse]:
        return list(reversed(self._read()[-limit:]))

    def mark_running(self, job_id: str) -> bool:
        return self._update(
            job_id,
            status="running",
            started_at=datetime.now(UTC),
            error_message=None,
        )

    def mark_completed(
        self,
        job_id: str,
        *,
        fetched_rows: int,
        collected_symbols: int,
        inserted_rows: int,
        updated_rows: int,
        invalid_rows: int,
        missing_symbols: list[str],
        warnings: list[str],
    ) -> bool:
        return self._update(
            job_id,
            status="completed",
            fetched_rows=fetched_rows,
            collected_symbols=collected_symbols,
            inserted_rows=inserted_rows,
            updated_rows=updated_rows,
            invalid_rows=invalid_rows,
            missing_symbols=missing_symbols,
            warnings=warnings,
            scanner_refresh_required=True,
            completed_at=datetime.now(UTC),
            error_message=None,
        )

    def mark_failed(self, job_id: str, message: str, warnings: list[str] | None = None) -> bool:
        return self._update(
            job_id,
            status="failed",
            warnings=warnings or [],
            error_message=message[:2000],
            completed_at=datetime.now(UTC),
            scanner_refresh_required=False,
        )

    def _update(self, job_id: str, **values: object) -> bool:
        with self._lock:
            jobs = self._read()
            for index, job in enumerate(jobs):
                if job.job_id == job_id:
                    jobs[index] = job.model_copy(update=values)
                    self._write(jobs)
                    return True
        return False

    def _read(self) -> list[CollectorRunResponse]:
        if not self.storage_path.is_file():
            return []
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return []
            return [CollectorRunResponse.model_validate(item) for item in payload]
        except (OSError, json.JSONDecodeError, ValidationError, TypeError):
            return []

    def _write(self, jobs: list[CollectorRunResponse]) -> None:
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
                json.dump(
                    [job.model_dump(mode="json") for job in jobs],
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
            os.replace(temp_path, self.storage_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
