"""Database persistence for DSE collector jobs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import CollectorRun
from app.schemas.collector import CollectorRunResponse


class CollectorRepository:
    """Create and update collector jobs without exposing database details."""

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager

    def is_available(self) -> bool:
        return self._manager.has_tables(("collector_runs",))

    def create(self, trade_date: date, source: str) -> CollectorRunResponse | None:
        if not self.is_available():
            return None
        record = CollectorRun(
            job_id=str(uuid4()),
            status="queued",
            requested_trade_date=trade_date,
            source=source,
        )
        try:
            with self._manager.session() as session:
                session.add(record)
                session.commit()
                session.refresh(record)
                return self._to_schema(record)
        except (SQLAlchemyError, RuntimeError):
            return None

    def get_active(self) -> CollectorRunResponse | None:
        if not self.is_available():
            return None
        try:
            with self._manager.session() as session:
                record = session.scalar(
                    select(CollectorRun)
                    .where(CollectorRun.status.in_(("queued", "running")))
                    .order_by(CollectorRun.id.desc())
                    .limit(1)
                )
                return None if record is None else self._to_schema(record)
        except (SQLAlchemyError, RuntimeError):
            return None

    def get(self, job_id: str) -> CollectorRunResponse | None:
        if not self.is_available():
            return None
        try:
            with self._manager.session() as session:
                record = session.scalar(select(CollectorRun).where(CollectorRun.job_id == job_id))
                return None if record is None else self._to_schema(record)
        except (SQLAlchemyError, RuntimeError):
            return None

    def latest(self) -> CollectorRunResponse | None:
        if not self.is_available():
            return None
        try:
            with self._manager.session() as session:
                record = session.scalar(select(CollectorRun).order_by(CollectorRun.id.desc()).limit(1))
                return None if record is None else self._to_schema(record)
        except (SQLAlchemyError, RuntimeError):
            return None

    def history(self, limit: int = 20) -> list[CollectorRunResponse]:
        if not self.is_available():
            return []
        try:
            with self._manager.session() as session:
                records = list(
                    session.scalars(select(CollectorRun).order_by(CollectorRun.id.desc()).limit(limit)).all()
                )
                return [self._to_schema(record) for record in records]
        except (SQLAlchemyError, RuntimeError):
            return []

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
            missing_symbols_json=missing_symbols,
            warnings_json=warnings,
            scanner_refresh_required=True,
            completed_at=datetime.now(UTC),
            error_message=None,
        )

    def mark_failed(self, job_id: str, message: str, warnings: list[str] | None = None) -> bool:
        return self._update(
            job_id,
            status="failed",
            warnings_json=warnings or [],
            error_message=message[:2000],
            completed_at=datetime.now(UTC),
            scanner_refresh_required=False,
        )

    def _update(self, job_id: str, **values: object) -> bool:
        if not self.is_available():
            return False
        try:
            with self._manager.session() as session:
                record = session.scalar(select(CollectorRun).where(CollectorRun.job_id == job_id))
                if record is None:
                    return False
                for key, value in values.items():
                    setattr(record, key, value)
                session.commit()
        except (SQLAlchemyError, RuntimeError):
            return False
        return True

    @staticmethod
    def _to_schema(record: CollectorRun) -> CollectorRunResponse:
        return CollectorRunResponse(
            job_id=record.job_id,
            status=record.status,  # type: ignore[arg-type]
            requested_trade_date=record.requested_trade_date,
            source=record.source,
            fetched_rows=record.fetched_rows,
            collected_symbols=record.collected_symbols,
            inserted_rows=record.inserted_rows,
            updated_rows=record.updated_rows,
            invalid_rows=record.invalid_rows,
            missing_symbols=list(record.missing_symbols_json),
            warnings=list(record.warnings_json),
            error_message=record.error_message,
            scanner_refresh_required=record.scanner_refresh_required,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
        )
