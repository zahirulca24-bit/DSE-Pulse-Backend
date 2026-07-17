"""SQLAlchemy models for optional OHLC and scanner persistence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative model base."""


class OhlcDaily(Base):
    """Normalized daily DSE OHLC records."""

    __tablename__ = "ohlc_daily"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_ohlc_daily_symbol_trade_date"),
        Index("ix_ohlc_daily_symbol", "symbol"),
        Index("ix_ohlc_daily_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trade: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ScannerRun(Base):
    """One persisted manual scanner run."""

    __tablename__ = "scanner_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    data_source: Mapped[str] = mapped_column(String(32), nullable=False)
    scanned_symbols: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_symbols: Mapped[int] = mapped_column(Integer, nullable=False)
    qualified_count: Mapped[int] = mapped_column(Integer, nullable=False)
    watch_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScannerCandidateRecord(Base):
    """A final candidate linked to one scanner run."""

    __tablename__ = "scanner_candidates"
    __table_args__ = (Index("ix_scanner_candidates_run_id", "run_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scanner_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grade: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_status: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_status: Mapped[str] = mapped_column(String(32), nullable=False)
    setup: Mapped[str] = mapped_column(String(64), nullable=False)
    latest_close: Mapped[float] = mapped_column(Float, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    trend: Mapped[str] = mapped_column(String(32), nullable=False)
    ema20: Mapped[float] = mapped_column(Float, nullable=False)
    ema50: Mapped[float] = mapped_column(Float, nullable=False)
    sma20: Mapped[float] = mapped_column(Float, nullable=False)
    sma50: Mapped[float] = mapped_column(Float, nullable=False)
    rsi14: Mapped[float] = mapped_column(Float, nullable=False)
    volume_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=False)
    reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    data_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def safe_text_fields(self) -> tuple[str, ...]:
        """Return textual fields useful for safety-oriented tests."""

        values: list[Any] = [self.setup, *self.reasons_json, *self.warnings_json]
        return tuple(str(value) for value in values)
