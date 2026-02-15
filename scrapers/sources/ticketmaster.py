"""Ticketmaster events via the Discovery API v2."""

from __future__ import annotations

import os
from datetime import datetime

from scrapers.base import BaseScraper, register
from scrapers.models import Event

_ENDPOINT = "https://app.ticketmaster.com/discovery/v2/events.json"
_DMA_NYC = "345"
_PAGE_SIZE = 200  # API max


@register
class TicketmasterScraper(BaseScraper):
    name = "ticketmaster"
    rate_limit = 0.25  # 5 req/s quota

    async def scrape(self) -> list[Event]:
        api_key = os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            raise RuntimeError("TICKETMASTER_API_KEY environment variable is required")

        events: list[Event] = []
        page = 0

        while True:
            params = {
                "apikey": api_key,
                "dmaId": _DMA_NYC,
                "size": _PAGE_SIZE,
                "page": page,
                "sort": "date,asc",
            }

            resp = await self.fetch(_ENDPOINT, params=params)
            data = resp.json()

            embedded = data.get("_embedded")
            if not embedded or "events" not in embedded:
                break

            for item in embedded["events"]:
                title = item.get("name", "")
                if not title:
                    continue

                dates = item.get("dates", {})
                start_obj = dates.get("start", {})
                start_dt_str = start_obj.get("dateTime")
                if not start_dt_str:
                    # Fall back to local date
                    local_date = start_obj.get("localDate")
                    if not local_date:
                        continue
                    start_time = datetime.fromisoformat(local_date)
                else:
                    start_time = datetime.fromisoformat(
                        start_dt_str.replace("Z", "+00:00")
                    )

                end_obj = dates.get("end", {})
                end_dt_str = end_obj.get("dateTime")
                end_time = (
                    datetime.fromisoformat(end_dt_str.replace("Z", "+00:00"))
                    if end_dt_str
                    else None
                )

                # Venue info
                venue_name = None
                address = None
                venues = (
                    item.get("_embedded", {}).get("venues", [])
                )
                if venues:
                    v = venues[0]
                    venue_name = v.get("name")
                    addr_obj = v.get("address", {})
                    city_obj = v.get("city", {})
                    state_obj = v.get("state", {})
                    addr_parts = [
                        addr_obj.get("line1"),
                        city_obj.get("name"),
                        state_obj.get("stateCode"),
                        v.get("postalCode"),
                    ]
                    address = ", ".join(p for p in addr_parts if p) or None

                # Category from classifications
                category = None
                classifications = item.get("classifications", [])
                if classifications:
                    seg = classifications[0].get("segment", {})
                    category = seg.get("name")

                # Best image
                image_url = None
                images = item.get("images", [])
                if images:
                    image_url = images[0].get("url")

                # Price range
                price = None
                price_ranges = item.get("priceRanges", [])
                if price_ranges:
                    pr = price_ranges[0]
                    lo = pr.get("min")
                    hi = pr.get("max")
                    currency = pr.get("currency", "USD")
                    if lo is not None and hi is not None:
                        price = f"{currency} {lo:.0f}-{hi:.0f}"
                    elif lo is not None:
                        price = f"From {currency} {lo:.0f}"

                events.append(
                    Event(
                        title=title,
                        description=item.get("info") or item.get("pleaseNote"),
                        url=item.get("url"),
                        venue=venue_name,
                        address=address,
                        start_time=start_time,
                        end_time=end_time,
                        category=category,
                        source=self.name,
                        source_id=item.get("id"),
                        image_url=image_url,
                        price=price,
                    )
                )

            # Pagination
            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 0)
            page += 1
            if page >= total_pages:
                break

        return events
