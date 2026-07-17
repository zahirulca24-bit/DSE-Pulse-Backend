"""Lazy optional SQLAlchemy engine and safe connection checks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@dataclass(frozen=True, slots=True)
class DatabaseConnectionStatus:
    """Internal safe database connection state."""

    configured: bool
    connected: bool
    message: str


class DatabaseManager:
    """Create a database engine lazily and never expose its configured URL."""

    def __init__(self, database_url: str | None) -> None:
        self._database_url = (database_url or "").strip()
        self._engine: Engine | None = None
        self._engine_failed = False

    @property
    def configured(self) -> bool:
        return bool(self._database_url)

    @property
    def engine(self) -> Engine | None:
        """Return a lazily created engine or None when configuration is invalid."""

        if not self.configured or self._engine_failed:
            return None
        if self._engine is not None:
            return self._engine
        try:
            url = self._normalize_url(self._database_url)
            kwargs: dict[str, object] = {"pool_pre_ping": True}
            if url.startswith("sqlite"):
                kwargs["connect_args"] = {"check_same_thread": False}
                if url.endswith(":memory:"):
                    kwargs["poolclass"] = StaticPool
            else:
                kwargs["connect_args"] = {"connect_timeout": 3}
            self._engine = create_engine(url, **kwargs)
        except (SQLAlchemyError, ValueError):
            self._engine_failed = True
            return None
        return self._engine

    def get_status(self) -> DatabaseConnectionStatus:
        """Test the connection using SELECT 1 and return a credential-free result."""

        if not self.configured:
            return DatabaseConnectionStatus(
                configured=False,
                connected=False,
                message="DATABASE_URL is not configured.",
            )
        engine = self.engine
        if engine is None:
            return DatabaseConnectionStatus(
                configured=True,
                connected=False,
                message="Database connection is unavailable.",
            )
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return DatabaseConnectionStatus(
                configured=True,
                connected=False,
                message="Database connection is unavailable.",
            )
        return DatabaseConnectionStatus(
            configured=True,
            connected=True,
            message="Database connection is available.",
        )

    def has_tables(self, table_names: tuple[str, ...]) -> bool:
        """Return true only when connected and all required tables exist."""

        status = self.get_status()
        engine = self.engine
        if not status.connected or engine is None:
            return False
        try:
            inspector = inspect(engine)
            return all(inspector.has_table(table_name) for table_name in table_names)
        except SQLAlchemyError:
            return False

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a transaction-capable session for a configured engine."""

        engine = self.engine
        if engine is None:
            raise RuntimeError("Database engine is unavailable.")
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    @staticmethod
    def _normalize_url(url: str) -> str:
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url
