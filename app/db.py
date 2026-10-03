"""Database connection and session management.

SQLite locally, Postgres in production — only the URL changes, because
SQLAlchemy abstracts the dialect away.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

LOGGER = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Parent class for every table model."""


# SQLite refuses cross-thread use by default, and FastAPI serves on a thread pool.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create tables that don't exist yet."""
    from pathlib import Path

    from . import models_db  # noqa: F401 — import so Base registers the tables

    if settings.database_url.startswith("sqlite:///"):
        db_file = settings.database_url.replace("sqlite:///", "")
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    LOGGER.info("Database ready at %s", settings.database_url)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()