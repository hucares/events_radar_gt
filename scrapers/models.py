"""Shared Pydantic models for NYC Events Radar."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, HttpUrl


class EventCategory(str, Enum):
    MUSIC = "music"
    THEATER = "theater"
    COMEDY = "comedy"
    ART = "art"
    FOOD = "food"
    SPORTS = "sports"
    NIGHTLIFE = "nightlife"
    OTHER = "other"


class Event(BaseModel):
    """Core event schema shared across scrapers, API, and frontend."""

    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    venue: str
    address: str | None = None
    borough: str | None = None
    category: EventCategory = EventCategory.OTHER
    price: str | None = None
    url: HttpUrl | None = None
    source: str
    source_id: str | None = None
    image_url: HttpUrl | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
