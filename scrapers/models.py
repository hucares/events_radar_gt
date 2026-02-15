"""Shared Pydantic event schema for NYC Events Radar."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class Event(BaseModel):
    """Core event schema shared across scrapers and API."""

    title: str
    description: str | None = None
    url: HttpUrl | None = None
    venue: str | None = None
    address: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    category: str | None = None
    source: str
    source_id: str | None = None
    image_url: HttpUrl | None = None
    price: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
