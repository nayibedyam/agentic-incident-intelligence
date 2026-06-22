import aiosqlite
from pathlib import Path

from src.config import settings

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(db_path))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
