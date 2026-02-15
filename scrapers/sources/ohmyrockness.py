"""Scraper for ohmyrockness.com/shows – NYC indie concert listings.

Note: ohmyrockness.com uses Cloudflare protection. The scraper attempts to
fetch the shows page directly; if the request is blocked by a JS challenge,
it logs a warning and returns an empty list rather than failing hard.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, register
from scrapers.models import Event

log = logging.getLogger(__name__)

BASE_URL = "https://www.ohmyrockness.com"
SHOWS_URL = f"{BASE_URL}/shows"


@register
class OhMyRocknessScraper(BaseScraper):
    name = "ohmyrockness"

    async def scrape(self) -> list[Event]:
        try:
            resp = await self.fetch(SHOWS_URL)
        except RuntimeError:
            log.warning("ohmyrockness.com blocked by Cloudflare – returning empty")
            return []

        # Detect Cloudflare challenge page
        if "Just a moment" in resp.text[:500] or "challenge-platform" in resp.text:
            log.warning("ohmyrockness.com served Cloudflare challenge – returning empty")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # OhMyRockness uses .show-card or .show-listing divs for show entries
        for card in soup.select(".show-card, .show-listing, .show, article.show"):
            try:
                event = self._parse_card(card)
                if event:
                    events.append(event)
            except Exception:
                continue

        # Fallback: try to find show links if card selectors don't match
        if not events:
            for link in soup.select("a[href*='/shows/']"):
                try:
                    event = self._parse_link(link)
                    if event:
                        events.append(event)
                except Exception:
                    continue

        return events

    def _parse_card(self, card: Tag) -> Event | None:
        # Title (band name)
        title_el = (
            card.select_one("h3, h2, .show-title, .band-name, .show-name")
        )
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        # URL
        link = card.select_one("a[href]") or card.find_parent("a")
        url = None
        source_id = None
        if link:
            href = link.get("href", "")
            url = f"{BASE_URL}{href}" if href.startswith("/") else href
            # Extract ID from URL path
            parts = href.strip("/").split("/")
            if parts:
                source_id = parts[-1]

        # Venue
        venue_el = card.select_one(".venue, .venue-name, .show-venue")
        venue = venue_el.get_text(strip=True) if venue_el else None

        # Date/time
        date_el = card.select_one(".date, .show-date, time")
        start_time = None
        if date_el:
            dt_attr = date_el.get("datetime")
            if dt_attr:
                start_time = _parse_iso(dt_attr)
            if not start_time:
                start_time = _parse_show_date(date_el.get_text(strip=True))

        if not start_time:
            return None

        # Price
        price_el = card.select_one(".price, .show-price, .ticket-price")
        price = price_el.get_text(strip=True) if price_el else None

        return Event(
            title=title,
            url=url,
            start_time=start_time,
            venue=venue,
            price=price,
            category="Music",
            source=self.name,
            source_id=source_id,
        )

    def _parse_link(self, link: Tag) -> Event | None:
        title = link.get_text(strip=True)
        if not title or len(title) < 2:
            return None

        href = link.get("href", "")
        url = f"{BASE_URL}{href}" if href.startswith("/") else href

        # Try to extract date from surrounding context
        parent = link.parent
        date_text = ""
        if parent:
            date_el = parent.find(class_=re.compile(r"date|time"))
            if date_el:
                date_text = date_el.get_text(strip=True)

        start_time = _parse_show_date(date_text) if date_text else None
        if not start_time:
            start_time = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)

        return Event(
            title=title,
            url=url,
            start_time=start_time,
            category="Music",
            source=self.name,
        )


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_show_date(text: str) -> datetime | None:
    """Try common date formats for show listings."""
    if not text:
        return None
    now = datetime.now()
    for fmt in (
        "%b %d, %Y",
        "%B %d, %Y",
        "%m/%d/%Y",
        "%b %d",
        "%B %d",
        "%A, %b %d",
        "%A, %B %d",
    ):
        try:
            dt = datetime.strptime(text.strip(), fmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt
        except ValueError:
            continue
    return None
