"""Eventbrite scraper – NYC event search listings."""

from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, register
from scrapers.models import Event


@register
class EventbriteScraper(BaseScraper):
    name = "eventbrite"
    rate_limit = 2.0

    SEARCH_URL = "https://www.eventbrite.com/d/ny--new-york/events/"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(self.SEARCH_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # Strategy 1: JSON-LD structured data (most reliable)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") != "Event":
                    continue
                event = self._from_jsonld(item)
                if event:
                    events.append(event)

        # Strategy 2: HTML event cards
        if not events:
            for card in soup.select("a[href*='/e/']"):
                event = self._from_card(card)
                if event:
                    events.append(event)

        return events

    def _from_jsonld(self, item: dict) -> Event | None:
        try:
            title = item.get("name", "").strip()
            start_raw = item.get("startDate", "")
            if not title or not start_raw:
                return None

            start_time = datetime.fromisoformat(start_raw)
            end_raw = item.get("endDate")
            end_time = datetime.fromisoformat(end_raw) if end_raw else None

            location = item.get("location", {})
            venue = location.get("name") if isinstance(location, dict) else None
            addr = location.get("address", {}) if isinstance(location, dict) else {}
            address = addr.get("streetAddress") if isinstance(addr, dict) else None

            image = item.get("image")
            if isinstance(image, list):
                image = image[0] if image else None

            offers = item.get("offers", {})
            price = self._extract_price(offers)

            url = item.get("url")
            return Event(
                title=title,
                description=(item.get("description") or "")[:500] or None,
                url=url,
                venue=venue,
                address=address,
                start_time=start_time,
                end_time=end_time,
                source=self.name,
                source_id=url.rstrip("/").split("-")[-1] if url else None,
                image_url=image,
                price=price,
            )
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_price(offers: dict | list) -> str | None:
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            return None
        raw = offers.get("price")
        if raw is None:
            return None
        try:
            val = float(raw)
            return "Free" if val == 0 else f"${val:.2f}"
        except (ValueError, TypeError):
            return str(raw)

    def _from_card(self, el) -> Event | None:
        try:
            href = el.get("href", "")
            if "/e/" not in href:
                return None

            title_el = el.find("h2") or el.find("h3")
            title = title_el.get_text(strip=True) if title_el else el.get_text(strip=True)
            if not title or len(title) < 3:
                return None

            time_el = el.find("time")
            if time_el and time_el.get("datetime"):
                start_time = datetime.fromisoformat(time_el["datetime"])
            else:
                start_time = datetime.now()

            url = href if href.startswith("http") else f"https://www.eventbrite.com{href}"
            return Event(
                title=title,
                url=url,
                start_time=start_time,
                source=self.name,
            )
        except (ValueError, TypeError):
            return None
