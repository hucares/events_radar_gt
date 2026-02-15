"""Dice.fm scraper – NYC events from city listing page."""

from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, register
from scrapers.models import Event


@register
class DiceScraper(BaseScraper):
    name = "dice"
    rate_limit = 2.0

    CITY_URL = "https://dice.fm/city/new-york"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(self.CITY_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # Strategy 1: __NEXT_DATA__ embedded JSON
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and next_data.string:
            try:
                data = json.loads(next_data.string)
                events = self._from_next_data(data)
            except json.JSONDecodeError:
                pass

        # Strategy 2: Embedded application state
        if not events:
            for script in soup.find_all("script"):
                text = script.string or ""
                match = re.search(
                    r"window\.__DICE_STATE__\s*=\s*({.+?});", text, re.DOTALL
                )
                if match:
                    try:
                        state = json.loads(match.group(1))
                        events = self._from_state(state)
                    except json.JSONDecodeError:
                        pass
                    break

        # Strategy 3: HTML event cards
        if not events:
            events = self._from_html(soup)

        return events

    def _from_next_data(self, data: dict) -> list[Event]:
        events: list[Event] = []
        props = data.get("props", {}).get("pageProps", {})
        for key in ("events", "initialEvents", "eventList", "data"):
            items = props.get(key, [])
            if isinstance(items, dict):
                items = items.get("data", items.get("events", []))
            if isinstance(items, list):
                for item in items:
                    event = self._parse_event(item)
                    if event:
                        events.append(event)
                if events:
                    break
        return events

    def _from_state(self, state: dict) -> list[Event]:
        events: list[Event] = []
        for key in ("events", "listings", "cityEvents"):
            items = state.get(key, [])
            if isinstance(items, list):
                for item in items:
                    event = self._parse_event(item)
                    if event:
                        events.append(event)
        return events

    def _parse_event(self, item: dict) -> Event | None:
        try:
            title = (item.get("name") or item.get("title", "")).strip()
            if not title:
                return None

            date_str = (
                item.get("date")
                or item.get("startDate")
                or item.get("start_date")
            )
            dates = item.get("dates")
            if not date_str and isinstance(dates, dict):
                date_str = dates.get("start")
            if not date_str:
                return None

            start_time = datetime.fromisoformat(
                date_str.replace("Z", "+00:00") if isinstance(date_str, str) else ""
            )

            end_str = item.get("endDate") or item.get("end_date")
            if not end_str and isinstance(dates, dict):
                end_str = dates.get("end")
            end_time = None
            if end_str and isinstance(end_str, str):
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

            venue_data = item.get("venue") or {}
            if isinstance(venue_data, str):
                venue, address = venue_data, None
            else:
                venue = venue_data.get("name")
                address = venue_data.get("address")

            url = item.get("url") or item.get("link")
            if url and not url.startswith("http"):
                url = f"https://dice.fm{url}"

            image_url = self._extract_image(item)

            raw_price = item.get("price") or item.get("cost")
            price = None
            if isinstance(raw_price, dict):
                price = raw_price.get("display") or raw_price.get("formatted")
            elif isinstance(raw_price, (int, float)):
                price = "Free" if raw_price == 0 else f"${raw_price:.2f}"
            elif raw_price is not None:
                price = str(raw_price)

            return Event(
                title=title,
                description=(item.get("description") or "")[:500] or None,
                url=url,
                venue=venue,
                address=address,
                start_time=start_time,
                end_time=end_time,
                category=item.get("genre") or item.get("category"),
                source=self.name,
                source_id=str(item.get("id", "")),
                image_url=image_url,
                price=price,
            )
        except (ValueError, TypeError, KeyError):
            return None

    @staticmethod
    def _extract_image(item: dict) -> str | None:
        images = item.get("images") or item.get("image")
        if isinstance(images, str):
            return images
        if isinstance(images, list) and images:
            first = images[0]
            return first if isinstance(first, str) else first.get("url")
        if isinstance(images, dict):
            return images.get("url") or images.get("src")
        return None

    def _from_html(self, soup: BeautifulSoup) -> list[Event]:
        events: list[Event] = []
        cards = soup.select("a[href*='/event/']")
        for card in cards:
            try:
                href = card.get("href", "")
                title_el = card.find("h3") or card.find("h2") or card.find("span")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3:
                    continue

                time_el = card.find("time")
                if time_el and time_el.get("datetime"):
                    start_time = datetime.fromisoformat(time_el["datetime"])
                else:
                    start_time = datetime.now()

                url = href if href.startswith("http") else f"https://dice.fm{href}"
                events.append(Event(
                    title=title,
                    url=url,
                    start_time=start_time,
                    source=self.name,
                ))
            except (ValueError, TypeError):
                continue
        return events
