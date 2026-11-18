"""SQLAlchemy engine and session dependency."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    """Yield a database session and always close it after the request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(engine_instance: Engine | None = None) -> None:
    """Initialize PostGIS extension and create all defined database tables."""
    target_engine = engine_instance or engine

    # In PostgreSQL, enable PostGIS extension first
    if target_engine.dialect.name == "postgresql":
        with target_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()

    # Import all models to ensure they are registered with Base.metadata
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=target_engine)

