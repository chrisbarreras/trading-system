"""
Database session management and connection handling.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import get_settings
from app.models.base import Base


# Create database engine
def get_engine():
    """
    Create and return SQLAlchemy engine.
    Uses database URL from settings.
    """
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        echo=settings.log_level == "DEBUG",  # Log SQL queries in debug mode
    )
    return engine


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Use this with FastAPI's Depends() to inject database sessions into endpoints.

    Example:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called on application startup.
    In production, use alembic migrations instead.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.
    WARNING: This will delete all data!
    Only use for testing or development.
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
