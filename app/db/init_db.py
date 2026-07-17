"""Create missing optional database tables without destructive operations."""

from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseManager
from app.db.models import Base


def initialize_database(manager: DatabaseManager) -> bool:
    """Create missing tables and preserve all existing tables and data."""

    engine = manager.engine
    if engine is None or not manager.get_status().connected:
        return False
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError:
        return False
    return True
