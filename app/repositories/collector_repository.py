"""Database persistence for DSE collector jobs and production collector state."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import CollectorRun, CollectorState, OhlcDaily
from app.schemas.collector import CollectorRunResponse, CollectorStatusResponse


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

    def fail_stale_active(self, max_age_minutes: int = 30) -> int:
        """Fail abandoned queued/running jobs so they cannot block future runs forever."""

        if not self.is_available():
            return 0
        cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        completed_at = datetime.now(UTC)
        try:
            with self._manager.session() as session:
                records = list(
                    session.scalars(
                        select(CollectorRun).where(
                            CollectorRun.status.in_(("queued", "running")),
                            or_(
                                CollectorRun.started_at < cutoff,
                                (CollectorRun.started_at.is_(None) & (CollectorRun.created_at < cutoff)),
                            ),
                        )
                    ).all()
                )
                for record in records:
                    record.status = "failed"
                    record.error_message = "Collector job expired before completion; start a new manual run."
                    record.completed_at = completed_at
                    record.scanner_refresh_required = False
                session.commit()
                return len(records)
        except (SQLAlchemyError, RuntimeError):
            return 0

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
            status=record.status,
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


class CollectorDbRepository(CollectorRepository):
    """Persist production collector state in the configured SQL database."""

    def is_available(self) -> bool:
        return self._manager.has_tables(("collector_state", "collector_runs", "ohlc_daily"))

    def jobs_available(self) -> bool:
        return self._manager.has_tables(("collector_runs",))

    def get_status(self, configured_source: str | None) -> CollectorStatusResponse:
        latest_trade_date = self._latest_trade_date()
        state = self._read_state()
        latest_run = self._latest_run()
        running = bool(latest_run and latest_run.status in {"queued", "running"})

        return CollectorStatusResponse(
            enabled=bool(state.enabled) if state else False,
            running=running,
            source=(state.source if state and state.source else configured_source),
            last_started_at=state.last_started_at if state else None,
            last_completed_at=state.last_completed_at if state else None,
            last_error=state.last_error if state else None,
            symbols_updated=state.symbols_updated if state else 0,
            inserted_rows=state.inserted_rows if state else 0,
            updated_rows=state.updated_rows if state else 0,
            rejected_rows=state.rejected_rows if state else 0,
            latest_trade_date=latest_trade_date,
        )

    def set_enabled(self, enabled: bool, source: str | None) -> CollectorStatusResponse:
        with self._manager.session() as session:
            state = session.get(CollectorState, 1)
            if state is None:
                state = CollectorState(id=1)
                session.add(state)
            state.enabled = enabled
            state.source = source
            state.last_error = None
            session.commit()
        return self.get_status(source)

    def mark_started(self, source: str) -> None:
        now = datetime.now(UTC)
        with self._manager.session() as session:
            state = session.get(CollectorState, 1)
            if state is None:
                state = CollectorState(id=1, enabled=True)
                session.add(state)
            state.source = source
            state.last_started_at = now
            state.last_error = None
            session.commit()

    def mark_completed(
        self,
        *,
        source: str,
        symbols_updated: int,
        inserted_rows: int,
        updated_rows: int,
        rejected_rows: int,
    ) -> None:
        now = datetime.now(UTC)
        with self._manager.session() as session:
            state = session.get(CollectorState, 1)
            if state is None:
                state = CollectorState(id=1, enabled=True)
                session.add(state)
            state.source = source
            state.last_completed_at = now
            state.last_error = None
            state.symbols_updated = symbols_updated
            state.inserted_rows = inserted_rows
            state.updated_rows = updated_rows
            state.rejected_rows = rejected_rows
            session.commit()

    def mark_failed(self, source: str | None, message: str) -> None:  # type: ignore[override]
        with self._manager.session() as session:
            state = session.get(CollectorState, 1)
            if state is None:
                state = CollectorState(id=1)
                session.add(state)
            state.source = source
            state.last_error = message[:2000]
            state.last_completed_at = datetime.now(UTC)
            session.commit()

    def _read_state(self) -> CollectorState | None:
        if not self.is_available():
            return None
        try:
            with self._manager.session() as session:
                return session.get(CollectorState, 1)
        except (SQLAlchemyError, RuntimeError):
            return None

    def _latest_run(self) -> CollectorRun | None:
        if not self.jobs_available():
            return None
        try:
            with self._manager.session() as session:
                return session.scalar(select(CollectorRun).order_by(CollectorRun.created_at.desc()).limit(1))
        except (SQLAlchemyError, RuntimeError):
            return None

    def _latest_trade_date(self) -> date | None:
        if not self._manager.has_tables(("ohlc_daily",)):
            return None
        try:
            with self._manager.session() as session:
                return session.scalar(select(func.max(OhlcDaily.trade_date)))
        except (SQLAlchemyError, RuntimeError):
            return None
