"""Scraper for donyc.com – NYC event listings."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, register
from scrapers.models import Event

BASE_URL = "https://donyc.com"
EVENTS_URL = f"{BASE_URL}/events"


@register
class DoNYCScraper(BaseScraper):
    name = "donyc"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(EVENTS_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        for card in soup.select(".ds-listing"):
            try:
                event = self._parse_card(card)
                if event:
                    events.append(event)
            except Exception:
                continue

        return events

    def _parse_card(self, card: Tag) -> Event | None:
        # Title & URL
        title_el = card.select_one("span[itemprop='name']")
        link_el = card.select_one("a[itemprop='url']")
        if not title_el or not link_el:
            return None

        title = title_el.get_text(strip=True)
        href = link_el.get("href", "")
        url = f"{BASE_URL}{href}" if href.startswith("/") else href

        # Dates
        start_meta = card.select_one("meta[itemprop='startDate']")
        end_meta = card.select_one("meta[itemprop='endDate']")
        if not start_meta:
            return None

        start_time = _parse_iso(start_meta.get("content", ""))
        if not start_time:
            return None
        end_time = _parse_iso(end_meta.get("content", "")) if end_meta else None

        # Venue
        loc = card.select_one("[itemprop='location']")
        venue = None
        address = None
        if loc:
            venue_el = loc.select_one("span[itemprop='name']")
            venue = venue_el.get_text(strip=True) if venue_el else None
            addr_el = loc.select_one("meta[itemprop='streetAddress']")
            address = addr_el.get("content") if addr_el else None

        # Image
        cover = card.select_one(".ds-cover-image")
        image_url = None
        if cover:
            style = cover.get("style", "")
            m = re.search(r"url\(['\"]?(https?://[^'\")\s]+)", style)
            if m:
                image_url = m.group(1)

        # Category from class like ds-event-category-music
        category = None
        for cls in card.get("class", []):
            if cls.startswith("ds-event-category-"):
                category = cls.replace("ds-event-category-", "").replace("-", " ").title()
                break

        # Price from banner text
        price = None
        banner = card.select_one(".ds-listing-banners")
        if banner:
            text = banner.get_text(" ", strip=True)
            if "Free" in text:
                price = "Free"

        # Source ID from permalink
        permalink = card.get("data-permalink", "")
        source_id = permalink.rstrip("/").rsplit("/", 1)[-1] if permalink else None

        return Event(
            title=title,
            url=url,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            address=address,
            image_url=image_url,
            category=category,
            price=price,
            source=self.name,
            source_id=source_id,
        )


def _parse_iso(value: str) -> datetime | None:
    """Parse ISO-ish datetime from DoNYC meta tags (e.g. 2026-02-15T19:00-0500)."""
    if not value:
        return None
    try:
        # Handle offset like -0500 (no colon)
        return datetime.fromisoformat(value.replace("-0500", "-05:00").replace("-0400", "-04:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
