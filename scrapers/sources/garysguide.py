"""Scraper for garysguide.com/events – NYC tech & startup events."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, register
from scrapers.models import Event

EVENTS_URL = "https://www.garysguide.com/events"


@register
class GarysGuideScraper(BaseScraper):
    name = "garysguide"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(EVENTS_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # Events live in <font class="ftitle"> anchor tags inside table rows
        for link in soup.select("font.ftitle a[href]"):
            try:
                event = self._parse_event(link)
                if event:
                    events.append(event)
            except Exception:
                continue

        return events

    def _parse_event(self, link: Tag) -> Event | None:
        title = link.get_text(strip=True)
        url = link.get("href", "")
        if not title or not url:
            return None

        # Extract source_id from URL like /events/qst5ykm/...
        source_id = None
        m = re.search(r"/events/([a-zA-Z0-9]+)/", url)
        if m:
            source_id = m.group(1)

        # Navigate up to the containing <tr>
        row = link.find_parent("tr")
        if not row:
            return None
        # The outer table row (parent of the nested table)
        outer_row = row.find_parent("tr")
        if not outer_row:
            outer_row = row

        tds = outer_row.find_all("td", recursive=False)
        if len(tds) < 3:
            return None

        # First TD: date + time
        date_td = tds[0]
        date_b = date_td.find("b")
        date_str = date_b.get_text(strip=True) if date_b else ""
        time_text = date_td.get_text(strip=True).replace(date_str, "").strip()
        start_time = _parse_datetime(date_str, time_text)
        if not start_time:
            return None

        # Price TD (third column)
        price_td = tds[2]
        price = price_td.get_text(strip=True)
        # Remove star image alt text
        for img in price_td.find_all("img"):
            alt = img.get("alt", "")
            price = price.replace(alt, "").strip()
        price = price if price else None

        # Venue & address from fdescription
        desc_el = outer_row.select_one("font.fdescription")
        venue = None
        address = None
        description = None
        if desc_el:
            desc_text = desc_el.get_text("\n", strip=True)
            lines = [l.strip() for l in desc_text.split("\n") if l.strip()]
            # First bold in fdescription is the venue
            venue_b = desc_el.find("b")
            if venue_b:
                venue_text = venue_b.get_text(strip=True)
                if venue_text.lower() != "venue":
                    venue = venue_text
                # Text after venue bold is the address
                remaining = []
                for sib in venue_b.next_siblings:
                    t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                    if t and t != ",":
                        remaining.append(t.lstrip(", "))
                if remaining:
                    address = remaining[0]
                    if len(remaining) > 1:
                        description = " ".join(remaining[1:])

        return Event(
            title=title,
            url=url,
            start_time=start_time,
            venue=venue,
            address=address,
            description=description,
            price=price,
            category="Tech",
            source=self.name,
            source_id=source_id,
        )


def _parse_datetime(date_str: str, time_str: str) -> datetime | None:
    """Parse Gary's Guide date/time like 'Feb 13' + '6:00pm'."""
    if not date_str:
        return None
    now = datetime.now()
    year = now.year
    combined = f"{date_str} {year} {time_str}".strip()
    for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y %I:%M %p", "%b %d %Y %I%p", "%b %d %Y"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    return None
