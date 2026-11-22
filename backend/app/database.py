"""
Database configuration and session management.

Provides SQLite / SQLAlchemy engine, session maker, declarative base,
and database initialization for the Healthcare Form Entity Extractor.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Database directory and default SQLite path
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "users.db"

# Allow override via DATABASE_URL environment variable
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# For SQLite, check_same_thread=False is needed for multi-threaded FastAPI workers
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Ensures the session is cleanly closed upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI request contexts.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def secure_db_permissions() -> None:
    """
    Ensure the SQLite database file has restrictive file permissions (0600: read/write owner only).
    Safely handles non-SQLite databases, non-existent files, and unsupported platforms (e.g. Windows).
    """
    if not DATABASE_URL.startswith("sqlite:///"):
        return
    db_file = Path(DATABASE_URL.replace("sqlite:///", ""))
    if db_file.exists() and db_file.is_file():
        try:
            # 0o600: Read/Write for owner only
            os.chmod(db_file, 0o600)
        except (OSError, PermissionError):
            pass


def init_db() -> None:
    """
    Initializes database tables if they do not already exist.
    Ensures parent storage directories are created and enforces 0600 file permissions.
    """
    if DATABASE_URL.startswith("sqlite:///"):
        db_file = Path(DATABASE_URL.replace("sqlite:///", ""))
        db_file.parent.mkdir(parents=True, exist_ok=True)

    # Import models so that Base.metadata has registered them
    from backend.app.models.user import UserModel  # noqa: F401
    from backend.app.models.revocation import RevokedTokenModel  # noqa: F401
    from backend.app.models.history import ExtractionHistoryModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
    secure_db_permissions()

