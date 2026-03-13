"""Database connection and session management."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dev:dev@localhost:5432/agent_platform",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    """Yield a database session, auto-closing on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
