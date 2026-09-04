"""
Database configuration and initialization
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import sys
from pathlib import Path


def _resolve_data_dir() -> Path:
    """Where report data (db, uploads, backups) lives.

    In a frozen PyInstaller build, __file__ resolves inside the onefile
    bootloader's per-launch extraction folder (%TEMP%\\_MEIxxxxxx on
    Windows), which is wiped after every run — anything stored relative to
    it never survives an app restart. Use a stable per-user data directory
    instead when frozen; dev runs keep the existing backend/data location.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / "PsychReportGen" / "data"
    return Path(__file__).parent.parent / "data"


# Create data directory if it doesn't exist
DATA_DIR = _resolve_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/reports.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize database tables"""
    from database.models import Report, Document, Template
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
