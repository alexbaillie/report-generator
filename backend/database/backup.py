"""Local, on-startup backups of the SQLite database.

Backups are written under data/backups/ (git-ignored, like the live DB) so
patient data never leaves the machine. Design goals:

- Run at startup: captures the previous session's final state — reliable even
  if the app was closed abruptly.
- Skip empty databases: a fresh/empty DB must never rotate out good backups.
- Skip unchanged databases: if nothing changed since the last backup, don't
  make a redundant copy (keeps the rotation window meaningful).
- Rotate: keep only the most recent MAX_BACKUPS files.
- Never fatal: a backup failure logs a warning but never blocks app startup.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from database.db import DATA_DIR

logger = logging.getLogger("uvicorn.error")

DB_PATH = DATA_DIR / "reports.db"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 15
_DATA_TABLES = ("reports", "templates", "documents")


def _db_has_data(db_path: Path) -> bool:
    """True if any core table exists and holds at least one row."""
    try:
        con = sqlite3.connect(db_path)
        try:
            existing = {
                row[0]
                for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            for table in _DATA_TABLES:
                if table in existing and con.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                    return True
            return False
        finally:
            con.close()
    except Exception:
        return False


def _source_fingerprint(db_path: Path) -> str:
    """Short content hash of the live DB, used to detect 'nothing changed'."""
    digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
    return digest[:12]


def _latest_backup_fingerprint() -> Optional[str]:
    """Fingerprint embedded in the most recent backup filename, if any."""
    backups = sorted(BACKUP_DIR.glob("reports-*.db"))
    if not backups:
        return None
    stem = backups[-1].stem  # reports-YYYYMMDD-HHMMSS-<fingerprint>
    parts = stem.split("-")
    return parts[-1] if len(parts) >= 4 else None


def _rotate(max_backups: int) -> None:
    backups = sorted(BACKUP_DIR.glob("reports-*.db"))  # names sort chronologically
    for stale in backups[: max(0, len(backups) - max_backups)]:
        stale.unlink(missing_ok=True)


def backup_database(max_backups: int = MAX_BACKUPS) -> Optional[Path]:
    """Create a rotating, deduplicated backup of the live database.

    Returns the backup path, or None if it was skipped or failed.
    """
    if not DB_PATH.exists() or not _db_has_data(DB_PATH):
        return None

    try:
        fingerprint = _source_fingerprint(DB_PATH)
    except Exception as error:  # unreadable DB — don't block startup
        logger.warning("Database backup skipped (could not read DB): %s", error)
        return None

    if fingerprint == _latest_backup_fingerprint():
        # Identical to the most recent backup — nothing changed since last launch.
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"reports-{stamp}-{fingerprint}.db"

    try:
        source = sqlite3.connect(DB_PATH)
        try:
            target = sqlite3.connect(dest)
            try:
                with target:
                    source.backup(target)  # consistent online copy (handles WAL/locks)
            finally:
                target.close()
        finally:
            source.close()
    except Exception as error:
        logger.warning("Database backup failed: %s", error)
        dest.unlink(missing_ok=True)
        return None

    _rotate(max_backups)
    logger.info("Database backed up to %s", dest.name)
    return dest
