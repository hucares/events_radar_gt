"""Scraper for cityguideny.com/events/ – NYC calendar of events."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, register
from scrapers.models import Event

BASE_URL = "https://cityguideny.com"
EVENTS_URL = f"{BASE_URL}/events/"


@register
class CityGuideNYScraper(BaseScraper):
    name = "cityguideny"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(EVENTS_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # Each event is an <a class="flex"> wrapping a .boxed-card
        for card_link in soup.select("a.flex[href*='/event/']"):
            try:
                event = self._parse_card(card_link)
                if event:
                    events.append(event)
            except Exception:
                continue

        return events

    def _parse_card(self, card_link: Tag) -> Event | None:
        href = card_link.get("href", "")
        url = f"{BASE_URL}{href}" if href.startswith("/") else href

        card = card_link.select_one(".boxed-card")
        if not card:
            return None

        # Title
        title_el = card.select_one("h3")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        # Date / time
        date_wrapper = card.select_one(".date-wrapper")
        start_time = None
        end_time = None
        price = None

        if date_wrapper:
            # Start date from .inline-block span
            start_span = date_wrapper.select_one(".inline-block")
            cal_span = date_wrapper.select_one(".calendar-date")

            if start_span:
                start_time = _parse_date(start_span.get_text(strip=True))

            if cal_span:
                cal_text = cal_span.get_text(" ", strip=True)
                # Parse end date and time from "Through Sunday Feb 15 | 11AM"
                end_time, time_str = _parse_through_date(cal_text)
                # Apply time to start_time
                if start_time and time_str:
                    start_time = _apply_time(start_time, time_str)

            # Price
            price_el = date_wrapper.select_one(".free-box")
            if price_el:
                price = price_el.get_text(strip=True)

        if not start_time:
            return None

        # Category from tooltip
        category_el = card.select_one(".tooltip-back")
        category = category_el.get_text(strip=True) if category_el else None

        # Venue
        venue_el = card.select_one("b")
        venue = venue_el.get_text(strip=True) if venue_el else None

        # Address
        addr_el = card.select_one("address")
        address = addr_el.get_text(strip=True) if addr_el else None

        # Description – text node after address
        description = None
        body = card.select_one(".event-body")
        if body:
            # Get all direct text content that isn't in a child element
            text_parts = []
            for child in body.children:
                if isinstance(child, str):
                    t = child.strip()
                    if t:
                        text_parts.append(t)
            if text_parts:
                description = " ".join(text_parts)

        # Source ID from URL slug
        source_id = href.strip("/").rsplit("/", 1)[-1] if href else None

        return Event(
            title=title,
            url=url,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            address=address,
            description=description,
            category=category,
            price=price,
            source=self.name,
            source_id=source_id,
        )


def _parse_date(text: str) -> datetime | None:
    """Parse date like 'Friday Feb 06' or 'Saturday Feb 14'."""
    if not text:
        return None
    now = datetime.now()
    # Remove day-of-week prefix
    text = re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+", "", text)
    for fmt in ("%b %d", "%B %d", "%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(text.strip(), fmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt
        except ValueError:
            continue
    return None


def _parse_through_date(text: str) -> tuple[datetime | None, str | None]:
    """Parse 'Through Sunday Feb 15 | 11AM' into end datetime + time string."""
    if not text:
        return None, None
    # Split on pipe for time portion
    time_str = None
    if "|" in text:
        parts = text.split("|", 1)
        text = parts[0].strip()
        time_str = parts[1].strip()

    # Remove "Through" prefix
    text = re.sub(r"^Through\s+", "", text, flags=re.IGNORECASE)
    end_dt = _parse_date(text)

    if end_dt and time_str:
        end_dt = _apply_time(end_dt, time_str)

    return end_dt, time_str


def _apply_time(dt: datetime, time_str: str) -> datetime:
    """Apply a time string like '11AM' or '7:30PM' to a date."""
    time_str = time_str.strip().upper()
    for fmt in ("%I%p", "%I:%M%p", "%I %p", "%I:%M %p"):
        try:
            t = datetime.strptime(time_str, fmt)
            return dt.replace(hour=t.hour, minute=t.minute)
        except ValueError:
            continue
    return dt
