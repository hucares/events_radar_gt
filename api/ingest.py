"""Ingest scraped JSON data into SQLite."""

import json
import sys
from pathlib import Path

import aiosqlite

# Allow importing scrapers package from sibling directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.models import Event  # noqa: E402

from .database import DATABASE_PATH  # noqa: E402

SCRAPERS_OUTPUT = Path(__file__).parent.parent / "scrapers" / "output"

NYC_BOROUGHS = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "staten island": "Staten Island",
}


def extract_borough(address: str | None) -> str | None:
    """Extract NYC borough from an address string."""
    if not address:
        return None
    addr_lower = address.lower()
    for key, borough in NYC_BOROUGHS.items():
        if key in addr_lower:
            return borough
    # Default "New York, NY" addresses to Manhattan
    if "new york" in addr_lower or ", ny " in addr_lower:
        return "Manhattan"
    return None


def check_is_free(price: str | None) -> bool:
    """Determine if an event is free based on its price string."""
    if price is None:
        return False
    cleaned = price.strip().lower()
    return cleaned in ("", "free", "$0", "$0.00", "0", "0.00")


async def ingest_events() -> int:
    """Read JSON files from scrapers/output/ and upsert into SQLite.

    Returns the number of events processed.
    """
    if not SCRAPERS_OUTPUT.exists():
        return 0

    count = 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for json_file in sorted(SCRAPERS_OUTPUT.glob("*.json")):
            with open(json_file) as f:
                data = json.load(f)

            events = data if isinstance(data, list) else [data]

            for raw in events:
                event = Event(**raw)
                borough = extract_borough(event.address)
                is_free = check_is_free(event.price)
                venue = event.venue or ""

                await db.execute(
                    """
                    INSERT INTO events (
                        title, description, url, venue, address, borough,
                        start_time, end_time, category, source, source_id,
                        image_url, price, is_free, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(title, start_time, venue) DO UPDATE SET
                        description = excluded.description,
                        url = excluded.url,
                        address = excluded.address,
                        borough = excluded.borough,
                        end_time = excluded.end_time,
                        category = excluded.category,
                        source_id = excluded.source_id,
                        image_url = excluded.image_url,
                        price = excluded.price,
                        is_free = excluded.is_free,
                        updated_at = datetime('now')
                    """,
                    (
                        event.title,
                        event.description,
                        str(event.url) if event.url else None,
                        venue,
                        event.address,
                        borough,
                        event.start_time.isoformat(),
                        event.end_time.isoformat() if event.end_time else None,
                        event.category,
                        event.source,
                        event.source_id,
                        str(event.image_url) if event.image_url else None,
                        event.price,
                        int(is_free),
                        event.created_at.isoformat() if event.created_at else None,
                        event.updated_at.isoformat() if event.updated_at else None,
                    ),
                )
                count += 1

        await db.commit()

    return count
