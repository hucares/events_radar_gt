"""Database setup and connection management for NYC Events Radar."""

from pathlib import Path

import aiosqlite

DATABASE_PATH = Path(__file__).parent.parent / "events.db"


async def get_db() -> aiosqlite.Connection:
    """Get a database connection with row factory enabled."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """Initialize database schema with events table and FTS5 index."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                venue TEXT NOT NULL DEFAULT '',
                address TEXT,
                borough TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                category TEXT,
                source TEXT NOT NULL,
                source_id TEXT,
                image_url TEXT,
                price TEXT,
                is_free INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(title, start_time, venue)
            );

            CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
            CREATE INDEX IF NOT EXISTS idx_events_borough ON events(borough);
            CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
            CREATE INDEX IF NOT EXISTS idx_events_start_time ON events(start_time);
            CREATE INDEX IF NOT EXISTS idx_events_is_free ON events(is_free);
        """)

        # FTS5 virtual table for full-text search on title, description, venue
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                title, description, venue,
                content='events',
                content_rowid='id'
            )
        """)

        # Triggers to keep FTS index in sync with events table
        await db.executescript("""
            CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
                INSERT INTO events_fts(rowid, title, description, venue)
                VALUES (new.id, new.title, new.description, new.venue);
            END;

            CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, venue)
                VALUES ('delete', old.id, old.title, old.description, old.venue);
            END;

            CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, venue)
                VALUES ('delete', old.id, old.title, old.description, old.venue);
                INSERT INTO events_fts(rowid, title, description, venue)
                VALUES (new.id, new.title, new.description, new.venue);
            END;
        """)

        await db.commit()
