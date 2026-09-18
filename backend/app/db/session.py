"""
Database Engine and Session Factory.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from ..core.config import settings

logger = logging.getLogger("zaslon.db")

# Use pool_pre_ping for MySQL connection resilience
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
