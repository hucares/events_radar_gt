"""Scraper for nyc-arts.org – NYC arts organization listings.

NYC-ARTS is no longer actively maintained but still serves its organization
directory. This scraper pulls the A–Z organization pages and converts each
entry into an Event-compatible record so downstream systems can discover
arts venues and their programming descriptions.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, register
from scrapers.models import Event

log = logging.getLogger(__name__)

BASE_URL = "https://www.nyc-arts.org"
ORGS_URL = f"{BASE_URL}/organizations/"


@register
class NYCArtsScraper(BaseScraper):
    name = "nyc_arts"

    async def scrape(self) -> list[Event]:
        events: list[Event] = []
        page = 1

        while True:
            url = ORGS_URL if page == 1 else f"{ORGS_URL}?letter=&paged={page}"
            try:
                resp = await self.fetch(url)
            except RuntimeError:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.org-list-item")
            if not articles:
                break

            for article in articles:
                try:
                    event = self._parse_org(article)
                    if event:
                        events.append(event)
                except Exception:
                    continue

            # Check for next page
            next_link = soup.select_one("a.next")
            if not next_link:
                break
            page += 1

            # Safety cap
            if page > 20:
                break

        return events

    def _parse_org(self, article: Tag) -> Event | None:
        title_el = article.select_one(".entry-title a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        # Location
        meta_el = article.select_one(".entry-meta")
        address = meta_el.get_text(strip=True) if meta_el else None

        # Description
        content_el = article.select_one(".entry-content p")
        description = content_el.get_text(strip=True) if content_el else None

        # Extract source_id from URL slug
        source_id = href.rstrip("/").rsplit("/", 1)[-1] if href else None

        # Category from page nav context
        categories = article.select(".category a, .tag a")
        category = categories[0].get_text(strip=True) if categories else "Arts"

        return Event(
            title=title,
            url=url,
            description=description,
            venue=title,
            address=address,
            start_time=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            category=category,
            source=self.name,
            source_id=source_id,
        )
