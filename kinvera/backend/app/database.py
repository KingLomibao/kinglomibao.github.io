"""
Database engine and session setup.

This module is the one place that knows how to talk to PostgreSQL.
Everything else (models, domain logic, API routes) receives a `Session`
object rather than connecting to the database itself. That separation
means we can point tests at a different database just by overriding
`get_db`, without touching any business logic.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    Using a generator with try/finally guarantees the session (and its
    underlying connection) is always closed, even if a request raises
    an exception halfway through.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
