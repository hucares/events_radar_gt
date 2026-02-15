"""Meetup scraper – NYC events from meetup.com/find."""

from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, register
from scrapers.models import Event


@register
class MeetupScraper(BaseScraper):
    name = "meetup"
    rate_limit = 2.0

    FIND_URL = "https://www.meetup.com/find/?location=us--ny--New+York&source=EVENTS"

    async def scrape(self) -> list[Event]:
        resp = await self.fetch(self.FIND_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # Strategy 1: __NEXT_DATA__ (Next.js embedded props)
        next_script = soup.find("script", id="__NEXT_DATA__")
        if next_script and next_script.string:
            try:
                data = json.loads(next_script.string)
                events = self._from_next_data(data)
            except json.JSONDecodeError:
                pass

        # Strategy 2: JSON-LD structured data
        if not events:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                except json.JSONDecodeError:
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Event":
                        event = self._from_jsonld(item)
                        if event:
                            events.append(event)

        # Strategy 3: HTML event cards
        if not events:
            events = self._from_html(soup)

        return events

    def _from_next_data(self, data: dict) -> list[Event]:
        events: list[Event] = []
        props = data.get("props", {}).get("pageProps", {})
        for key in ("events", "recommendedEvents", "results"):
            items = props.get(key)
            if isinstance(items, dict):
                items = items.get("edges", items.get("nodes", []))
            if isinstance(items, list):
                for item in items:
                    # Handle GraphQL edge/node pattern
                    node = item.get("node", item) if isinstance(item, dict) else item
                    if isinstance(node, dict):
                        event = self._parse_event(node)
                        if event:
                            events.append(event)
                if events:
                    break
        return events

    def _parse_event(self, item: dict) -> Event | None:
        try:
            title = (item.get("title") or item.get("name", "")).strip()
            if not title:
                return None

            date_str = (
                item.get("dateTime")
                or item.get("start_time")
                or item.get("local_date")
            )
            if not date_str:
                return None

            if isinstance(date_str, (int, float)):
                start_time = datetime.fromtimestamp(date_str / 1000)
            else:
                start_time = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )

            end_str = item.get("endTime") or item.get("end_time")
            end_time = None
            if end_str:
                if isinstance(end_str, (int, float)):
                    end_time = datetime.fromtimestamp(end_str / 1000)
                else:
                    end_time = datetime.fromisoformat(
                        end_str.replace("Z", "+00:00")
                    )

            venue_data = item.get("venue") or {}
            venue = venue_data.get("name") if isinstance(venue_data, dict) else None
            address = None
            if isinstance(venue_data, dict):
                parts = [
                    venue_data.get("address_1", ""),
                    venue_data.get("city", ""),
                    venue_data.get("state", ""),
                ]
                address = ", ".join(p for p in parts if p) or None

            event_url = item.get("eventUrl") or item.get("link") or item.get("url")
            if event_url and not event_url.startswith("http"):
                event_url = f"https://www.meetup.com{event_url}"

            group = item.get("group", {})
            category = None
            if isinstance(group, dict):
                topics = group.get("topics") or group.get("topicCategory")
                if isinstance(topics, list) and topics:
                    first = topics[0]
                    category = first.get("name") if isinstance(first, dict) else str(first)
                elif isinstance(topics, dict):
                    category = topics.get("name")

            image_url = item.get("imageUrl") or item.get("image_url")
            if not image_url and isinstance(item.get("featuredPhoto"), dict):
                image_url = (
                    item["featuredPhoto"].get("highres_link")
                    or item["featuredPhoto"].get("photo_link")
                )

            fee = item.get("fee") or item.get("feeSettings")
            price = None
            if isinstance(fee, dict):
                amount = fee.get("amount")
                if amount is not None:
                    price = "Free" if float(amount) == 0 else f"${amount}"
                elif fee.get("required") is False:
                    price = "Free"
            elif item.get("is_free") or item.get("isFree"):
                price = "Free"

            return Event(
                title=title,
                description=(item.get("description") or "")[:500] or None,
                url=event_url,
                venue=venue,
                address=address,
                start_time=start_time,
                end_time=end_time,
                category=category,
                source=self.name,
                source_id=str(item.get("id", "")),
                image_url=image_url,
                price=price,
            )
        except (ValueError, TypeError, KeyError):
            return None

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

            return Event(
                title=title,
                description=(item.get("description") or "")[:500] or None,
                url=item.get("url"),
                venue=venue,
                address=address,
                start_time=start_time,
                end_time=end_time,
                source=self.name,
                image_url=item.get("image"),
            )
        except (ValueError, TypeError):
            return None

    def _from_html(self, soup: BeautifulSoup) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        for card in soup.select("a[href*='/events/']"):
            try:
                href = card.get("href", "")
                if href in seen or "/events/" not in href:
                    continue
                seen.add(href)

                title_el = card.find("h2") or card.find("h3") or card.find("span")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3:
                    continue

                time_el = card.find("time")
                if time_el and time_el.get("datetime"):
                    start_time = datetime.fromisoformat(time_el["datetime"])
                else:
                    start_time = datetime.now()

                url = href if href.startswith("http") else f"https://www.meetup.com{href}"
                events.append(Event(
                    title=title,
                    url=url,
                    start_time=start_time,
                    source=self.name,
                ))
            except (ValueError, TypeError):
                continue
        return events
