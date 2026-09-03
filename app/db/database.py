from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""


engine = create_engine(
    settings.database_url,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for FastAPI requests."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()