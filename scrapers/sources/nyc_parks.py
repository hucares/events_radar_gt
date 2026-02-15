"""NYC Parks events via the Socrata (SODA) Open Data API."""

from __future__ import annotations

import os
from datetime import datetime

from scrapers.base import BaseScraper, register
from scrapers.models import Event

_ENDPOINT = "https://data.cityofnewyork.us/resource/w3wp-dpdi.json"
_PAGE_SIZE = 1000


@register
class NYCParksScraper(BaseScraper):
    name = "nyc_parks"
    rate_limit = 0.5

    async def scrape(self) -> list[Event]:
        events: list[Event] = []
        offset = 0

        while True:
            params = {
                "$limit": _PAGE_SIZE,
                "$offset": offset,
                "$order": "start_date_time ASC",
            }
            # Socrata app tokens are optional but raise throttle limits.
            app_token = os.environ.get("NYC_OPEN_DATA_APP_TOKEN")
            if app_token:
                params["$$app_token"] = app_token

            resp = await self.fetch(_ENDPOINT, params=params)
            rows = resp.json()

            if not rows:
                break

            for row in rows:
                title = row.get("title") or row.get("name") or ""
                if not title:
                    continue

                start_raw = row.get("start_date_time")
                if not start_raw:
                    continue

                start_time = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))

                end_raw = row.get("end_date_time")
                end_time = (
                    datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                    if end_raw
                    else None
                )

                location = row.get("location") or ""
                address_parts = [
                    row.get("address"),
                    row.get("borough"),
                    row.get("zip"),
                ]
                address = ", ".join(p for p in address_parts if p) or None

                events.append(
                    Event(
                        title=title,
                        description=row.get("description"),
                        url=row.get("url") or None,
                        venue=location or None,
                        address=address,
                        start_time=start_time,
                        end_time=end_time,
                        category=row.get("category") or None,
                        source=self.name,
                        source_id=row.get("uid") or row.get("id") or None,
                        image_url=row.get("image") or None,
                        price=row.get("cost_description") or None,
                    )
                )

            if len(rows) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        return events
