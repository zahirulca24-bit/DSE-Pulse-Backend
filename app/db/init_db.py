"""Create and safely upgrade optional database tables."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import Base

_SCANNER_TABLE = "scanner_candidates"
_REQUIRED_SCANNER_COLUMNS = {
    "qualification_passed",
    "qualification_failures_json",
    "entry_distance_percent",
}


def initialize_database(manager: DatabaseManager) -> bool:
    """Create missing tables and apply additive scanner schema upgrades."""

    engine = manager.engine
    if engine is None or not manager.get_status().connected:
        return False
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            _upgrade_scanner_candidates(connection)
    except (SQLAlchemyError, RuntimeError):
        return False
    return True


def _upgrade_scanner_candidates(connection: Connection) -> None:
    """Upgrade legacy scanner candidate tables without dropping valid runs."""

    inspector = inspect(connection)
    if _SCANNER_TABLE not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(_SCANNER_TABLE)}
    dialect = connection.dialect.name

    if "qualification_passed" not in existing_columns:
        default = "FALSE" if dialect == "postgresql" else "0"
        connection.execute(
            text(
                "ALTER TABLE scanner_candidates "
                f"ADD COLUMN qualification_passed BOOLEAN NOT NULL DEFAULT {default}"
            )
        )

    if "qualification_failures_json" not in existing_columns:
        if dialect == "postgresql":
            statement = (
                "ALTER TABLE scanner_candidates "
                "ADD COLUMN qualification_failures_json JSON NOT NULL DEFAULT '[]'::json"
            )
        else:
            statement = (
                "ALTER TABLE scanner_candidates "
                "ADD COLUMN qualification_failures_json JSON NOT NULL DEFAULT '[]'"
            )
        connection.execute(text(statement))

    if "entry_distance_percent" not in existing_columns:
        connection.execute(
            text("ALTER TABLE scanner_candidates ADD COLUMN entry_distance_percent FLOAT")
        )

    _remove_duplicate_candidates(connection, dialect)
    connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_scanner_candidates_run_symbol "
            "ON scanner_candidates (run_id, symbol)"
        )
    )

    upgraded_columns = {
        column["name"] for column in inspect(connection).get_columns(_SCANNER_TABLE)
    }
    if not _REQUIRED_SCANNER_COLUMNS.issubset(upgraded_columns):
        raise RuntimeError("Scanner candidate schema upgrade is incomplete.")


def _remove_duplicate_candidates(connection: Connection, dialect: str) -> None:
    """Keep the earliest row for each run/symbol before adding uniqueness."""

    if dialect == "postgresql":
        connection.execute(
            text(
                "DELETE FROM scanner_candidates duplicate "
                "USING scanner_candidates keeper "
                "WHERE duplicate.run_id = keeper.run_id "
                "AND UPPER(TRIM(duplicate.symbol)) = UPPER(TRIM(keeper.symbol)) "
                "AND duplicate.id > keeper.id"
            )
        )
    else:
        connection.execute(
            text(
                "DELETE FROM scanner_candidates "
                "WHERE id NOT IN ("
                "SELECT MIN(id) FROM scanner_candidates "
                "GROUP BY run_id, UPPER(TRIM(symbol))"
                ")"
            )
        )

    connection.execute(text("UPDATE scanner_candidates SET symbol = UPPER(TRIM(symbol))"))
