"""EDMTrain events via the EDMTrain API."""

from __future__ import annotations

import os
from datetime import datetime

from scrapers.base import BaseScraper, register
from scrapers.models import Event

_ENDPOINT = "https://edmtrain.com/api/events"


@register
class EDMTrainScraper(BaseScraper):
    name = "edmtrain"
    rate_limit = 1.0

    async def scrape(self) -> list[Event]:
        api_key = os.environ.get("EDMTRAIN_API_KEY")
        if not api_key:
            raise RuntimeError("EDMTRAIN_API_KEY environment variable is required")

        params = {
            "client": api_key,
            "state": "New York",
        }

        resp = await self.fetch(_ENDPOINT, params=params)
        data = resp.json()

        raw_events = data if isinstance(data, list) else data.get("data", [])

        events: list[Event] = []
        for item in raw_events:
            title = _build_title(item)
            if not title:
                continue

            date_str = item.get("date")
            if not date_str:
                continue
            start_time = datetime.fromisoformat(date_str)

            venue_obj = item.get("venue", {})
            venue_name = venue_obj.get("name")
            address = venue_obj.get("location")

            # Filter to NYC area
            state = venue_obj.get("state")
            if state and state != "New York":
                continue

            artists = item.get("artistList", [])
            description = ", ".join(
                a.get("name", "") for a in artists if a.get("name")
            ) or None

            event_url = None
            link = item.get("link")
            if link:
                event_url = (
                    link if link.startswith("http") else f"https://edmtrain.com{link}"
                )

            events.append(
                Event(
                    title=title,
                    description=description,
                    url=event_url,
                    venue=venue_name,
                    address=address,
                    start_time=start_time,
                    category="Music/EDM",
                    source=self.name,
                    source_id=str(item["id"]) if "id" in item else None,
                    image_url=item.get("image") or None,
                    price=item.get("ticketPrice") or None,
                )
            )

        return events


def _build_title(item: dict) -> str:
    """Build an event title from name or artist list."""
    name = item.get("name") or item.get("title")
    if name:
        return name
    artists = item.get("artistList", [])
    names = [a["name"] for a in artists if a.get("name")]
    if names:
        return ", ".join(names[:3]) + (" + more" if len(names) > 3 else "")
    return ""
