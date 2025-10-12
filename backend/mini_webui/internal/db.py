import os
import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import create_engine, MetaData, event, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

from ..config import DATABASE_URL
from sqlalchemy.engine import make_url

log = logging.getLogger(__name__)


class JSONField(types.TypeDecorator):
    """JSON field type for SQLAlchemy"""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect) -> Any:
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value: Optional[_T], dialect) -> Any:
        if value is not None:
            return json.loads(value)
        return value

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)


# SQLite database configuration
SQLALCHEMY_DATABASE_URL = DATABASE_URL

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # Ensure parent directory exists for SQLite file paths
    try:
        url = make_url(SQLALCHEMY_DATABASE_URL)
        db_path = url.database or ""
        # Ignore in-memory or special SQLite URLs
        if db_path and db_path not in (":memory:",):
            parent_dir = os.path.dirname(db_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
    except Exception as e:
        log.warning(f"Could not ensure SQLite directory exists: {e}")

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

    def on_connect(dbapi_connection, connection_record):
        """Enable WAL mode for better concurrency"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(engine, "connect", on_connect)
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)


SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    expire_on_commit=False
)

Base = declarative_base()
Session = scoped_session(SessionLocal)


def get_session():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
