"""NYC Events Radar API."""

import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Allow importing scrapers package from sibling directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.models import Event  # noqa: E402, F401

from .database import get_db, init_db  # noqa: E402
from .ingest import ingest_events  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ingest_events()
    yield


app = FastAPI(title="NYC Events Radar", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/events")
async def list_events(
    q: str | None = None,
    category: str | None = None,
    borough: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    is_free: bool | None = None,
    source: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List events with pagination and filtering."""
    db = await get_db()
    try:
        conditions: list[str] = []
        params: list = []

        if q:
            conditions.append(
                "e.id IN (SELECT rowid FROM events_fts WHERE events_fts MATCH ?)"
            )
            params.append(q)
        if category:
            conditions.append("e.category = ?")
            params.append(category)
        if borough:
            conditions.append("e.borough = ?")
            params.append(borough)
        if date_from:
            conditions.append("date(e.start_time) >= ?")
            params.append(date_from.isoformat())
        if date_to:
            conditions.append("date(e.start_time) <= ?")
            params.append(date_to.isoformat())
        if is_free is not None:
            conditions.append("e.is_free = ?")
            params.append(int(is_free))
        if source:
            conditions.append("e.source = ?")
            params.append(source)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Total count
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM events e {where_clause}", params
        )
        total = (await cursor.fetchone())[0]

        # Paginated results
        offset = (page - 1) * per_page
        cursor = await db.execute(
            f"SELECT e.* FROM events e {where_clause} "
            "ORDER BY e.start_time ASC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        rows = await cursor.fetchall()
        events = [dict(row) for row in rows]

        return {
            "events": events,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        }
    finally:
        await db.close()


@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    """Get a single event by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        return dict(row)
    finally:
        await db.close()


@app.get("/api/sources")
async def list_sources():
    """List all event sources with counts."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT source, COUNT(*) as count FROM events "
            "GROUP BY source ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
        return [{"source": row[0], "count": row[1]} for row in rows]
    finally:
        await db.close()


@app.get("/api/categories")
async def list_categories():
    """List all event categories with counts."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT category, COUNT(*) as count FROM events "
            "WHERE category IS NOT NULL "
            "GROUP BY category ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
        return [{"category": row[0], "count": row[1]} for row in rows]
    finally:
        await db.close()


@app.get("/api/stats")
async def get_stats():
    """Get aggregate statistics about events."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM events")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(DISTINCT source) FROM events")
        sources = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT category) FROM events WHERE category IS NOT NULL"
        )
        categories = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM events WHERE is_free = 1")
        free_events = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT borough) FROM events WHERE borough IS NOT NULL"
        )
        boroughs = (await cursor.fetchone())[0]

        return {
            "total_events": total,
            "total_sources": sources,
            "total_categories": categories,
            "free_events": free_events,
            "boroughs_covered": boroughs,
        }
    finally:
        await db.close()
