"""Resident Advisor scraper – reverse-engineered GraphQL API for NYC events."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from scrapers.base import BaseScraper, _USER_AGENTS, register
from scrapers.models import Event


@register
class ResidentAdvisorScraper(BaseScraper):
    name = "resident_advisor"
    rate_limit = 2.0

    GRAPHQL_URL = "https://ra.co/graphql"
    NYC_AREA_ID = 218

    EVENTS_QUERY = """
    query GET_DEFAULT_EVENTS_LISTING(
        $filters: FilterInputDtoInput
        $pageSize: Int
        $page: Int
    ) {
        eventListings(filters: $filters, pageSize: $pageSize, page: $page) {
            data {
                listingDate
                event {
                    id
                    title
                    date
                    startTime
                    endTime
                    contentUrl
                    images {
                        filename
                    }
                    venue {
                        id
                        name
                        address
                    }
                    pick {
                        blurb
                    }
                }
            }
            totalResults
        }
    }
    """

    async def scrape(self) -> list[Event]:
        client = await self._ensure_client()
        today = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

        payload = {
            "query": self.EVENTS_QUERY,
            "variables": {
                "filters": {
                    "areas": {"eq": self.NYC_AREA_ID},
                    "listingDate": {"gte": today, "lte": end_date},
                },
                "pageSize": 50,
                "page": 1,
            },
        }

        await self._rate_limit_wait()
        try:
            resp = await client.post(
                self.GRAPHQL_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Referer": "https://ra.co/events/us/newyork",
                    "User-Agent": random.choice(_USER_AGENTS),
                },
            )
            resp.raise_for_status()
        except Exception as exc:
            raise RuntimeError(
                f"[{self.name}] GraphQL request failed: {exc}"
            ) from exc

        data = resp.json()
        listings = data.get("data", {}).get("eventListings", {}).get("data", [])

        events: list[Event] = []
        for listing in listings:
            event = self._parse_listing(listing)
            if event:
                events.append(event)
        return events

    def _parse_listing(self, listing: dict) -> Event | None:
        try:
            ev = listing.get("event", {})
            title = ev.get("title", "").strip()
            if not title:
                return None

            date_str = ev.get("date") or listing.get("listingDate", "")
            start_str = ev.get("startTime")
            if start_str:
                start_time = datetime.fromisoformat(start_str)
            elif date_str:
                start_time = datetime.fromisoformat(date_str)
            else:
                return None

            end_str = ev.get("endTime")
            end_time = datetime.fromisoformat(end_str) if end_str else None

            venue_data = ev.get("venue") or {}
            venue = venue_data.get("name")
            address = venue_data.get("address")

            content_url = ev.get("contentUrl", "")
            url = f"https://ra.co{content_url}" if content_url else None

            images = ev.get("images", [])
            image_url = None
            if images:
                fname = images[0].get("filename", "")
                if fname:
                    image_url = f"https://ra.co/images/events/{fname}"

            description = None
            pick = ev.get("pick")
            if pick and isinstance(pick, dict):
                description = pick.get("blurb")

            return Event(
                title=title,
                description=description,
                url=url,
                venue=venue,
                address=address,
                start_time=start_time,
                end_time=end_time,
                category="music",
                source=self.name,
                source_id=str(ev.get("id", "")),
                image_url=image_url,
            )
        except (ValueError, TypeError):
            return None
