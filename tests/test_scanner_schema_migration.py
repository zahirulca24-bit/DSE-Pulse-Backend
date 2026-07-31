"""Regression coverage for additive scanner database upgrades."""

from pathlib import Path

from sqlalchemy import inspect, text

from app.db.database import DatabaseManager
from app.db.init_db import initialize_database


def test_initialize_database_upgrades_legacy_scanner_candidates(tmp_path: Path) -> None:
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'legacy.db'}")
    assert manager.engine is not None

    with manager.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE scanner_runs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "run_id VARCHAR(36) NOT NULL UNIQUE, "
                "mode VARCHAR(32) NOT NULL, data_source VARCHAR(32) NOT NULL, "
                "scanned_symbols INTEGER NOT NULL, eligible_symbols INTEGER NOT NULL, "
                "qualified_count INTEGER NOT NULL, watch_count INTEGER NOT NULL, "
                "rejected_count INTEGER NOT NULL, generated_at DATETIME NOT NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE scanner_candidates ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, run_id VARCHAR(36) NOT NULL, "
                "symbol VARCHAR(32) NOT NULL, company VARCHAR(255), sector VARCHAR(100), "
                "grade VARCHAR(16) NOT NULL, score INTEGER NOT NULL, "
                "signal_status VARCHAR(32) NOT NULL, entry_status VARCHAR(32) NOT NULL, "
                "setup VARCHAR(64) NOT NULL, latest_close FLOAT NOT NULL, "
                "trade_date DATE NOT NULL, trend VARCHAR(32) NOT NULL, "
                "ema20 FLOAT NOT NULL, ema50 FLOAT NOT NULL, sma20 FLOAT NOT NULL, "
                "sma50 FLOAT NOT NULL, rsi14 FLOAT NOT NULL, volume_ratio FLOAT NOT NULL, "
                "risk_reward FLOAT NOT NULL, reasons_json JSON NOT NULL, "
                "warnings_json JSON NOT NULL, data_mode VARCHAR(32) NOT NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        values = {
            "run_id": "run-1",
            "company": None,
            "sector": "Bank",
            "grade": "A",
            "score": 92,
            "signal_status": "qualified",
            "entry_status": "READY",
            "setup": "EMA Trend Pullback",
            "latest_close": 48.5,
            "trade_date": "2026-07-30",
            "trend": "BULLISH",
            "ema20": 48.0,
            "ema50": 46.0,
            "sma20": 47.8,
            "sma50": 45.9,
            "rsi14": 59.0,
            "volume_ratio": 1.8,
            "risk_reward": 1.75,
            "reasons_json": "[]",
            "warnings_json": "[]",
            "data_mode": "Database",
        }
        insert = text(
            "INSERT INTO scanner_candidates ("
            "run_id, symbol, company, sector, grade, score, signal_status, entry_status, "
            "setup, latest_close, trade_date, trend, ema20, ema50, sma20, sma50, rsi14, "
            "volume_ratio, risk_reward, reasons_json, warnings_json, data_mode) VALUES ("
            ":run_id, :symbol, :company, :sector, :grade, :score, :signal_status, "
            ":entry_status, :setup, :latest_close, :trade_date, :trend, :ema20, :ema50, "
            ":sma20, :sma50, :rsi14, :volume_ratio, :risk_reward, :reasons_json, "
            ":warnings_json, :data_mode)"
        )
        connection.execute(insert, values | {"symbol": " bracbank "})
        connection.execute(insert, values | {"symbol": "BRACBANK"})

    assert initialize_database(manager) is True

    inspector = inspect(manager.engine)
    columns = {column["name"] for column in inspector.get_columns("scanner_candidates")}
    assert {
        "qualification_passed",
        "qualification_failures_json",
        "entry_distance_percent",
    }.issubset(columns)

    with manager.engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT symbol, qualification_passed, qualification_failures_json "
                "FROM scanner_candidates"
            )
        ).all()
        indexes = inspect(connection).get_indexes("scanner_candidates")

    assert rows == [("BRACBANK", 0, "[]")]
    assert any(
        index["name"] == "uq_scanner_candidates_run_symbol" and index["unique"]
        for index in indexes
    )
