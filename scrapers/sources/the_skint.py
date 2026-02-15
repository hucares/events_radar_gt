"""The Skint scraper – daily NYC event blog posts."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, register
from scrapers.models import Event


@register
class TheSkintScraper(BaseScraper):
    name = "the_skint"
    rate_limit = 2.0

    BASE_URL = "https://theskint.com"

    async def scrape(self) -> list[Event]:
        # Fetch homepage to find the latest daily post
        resp = await self.fetch(self.BASE_URL)
        soup = BeautifulSoup(resp.text, "html.parser")

        post_url = self._find_latest_post(soup)
        if not post_url:
            return []

        # Fetch and parse the post
        post_resp = await self.fetch(post_url)
        post_soup = BeautifulSoup(post_resp.text, "html.parser")
        return self._parse_post(post_soup)

    def _find_latest_post(self, soup: BeautifulSoup) -> str | None:
        for selector in (
            "article a",
            "h2 a",
            ".entry-title a",
            ".post-title a",
            "a[rel='bookmark']",
        ):
            link = soup.select_one(selector)
            if link and link.get("href"):
                href = link["href"]
                return href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # Fall back to any link that looks like a date-based post path
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(r"/\d{4}/\d{2}/", href):
                return href if href.startswith("http") else f"{self.BASE_URL}{href}"
        return None

    def _parse_post(self, soup: BeautifulSoup) -> list[Event]:
        events: list[Event] = []
        content = (
            soup.find("div", class_="entry-content")
            or soup.find("div", class_="post-content")
            or soup.find("article")
        )
        if not content:
            return events

        for block in content.find_all(["p", "li"]):
            event = self._parse_block(block)
            if event:
                events.append(event)
        return events

    def _parse_block(self, block) -> Event | None:
        text = block.get_text(strip=True)
        if not text or len(text) < 15:
            return None

        # Skip boilerplate
        lower = text.lower()
        if any(
            kw in lower
            for kw in ("subscribe", "follow us", "copyright", "advertisement", "sign up")
        ):
            return None

        link = block.find("a", href=True)
        url = link["href"] if link else None

        # Title from bold text or link text
        bold = block.find(["strong", "b"])
        if bold:
            title = bold.get_text(strip=True)
        elif link:
            title = link.get_text(strip=True)
        else:
            title = text.split(".")[0].strip()

        if not title or len(title) < 5:
            return None

        start_time = self._extract_datetime(text)
        if not start_time:
            start_time = datetime.now().replace(
                hour=19, minute=0, second=0, microsecond=0
            )

        price = self._extract_price(text)
        venue = self._extract_venue(text)
        description = text if text != title else None

        return Event(
            title=title[:200],
            description=description[:500] if description else None,
            url=url,
            venue=venue,
            start_time=start_time,
            source=self.name,
            price=price,
        )

    @staticmethod
    def _extract_datetime(text: str) -> datetime | None:
        time_match = re.search(
            r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|a\.m\.|p\.m\.))", text
        )
        hour, minute = 19, 0
        if time_match:
            raw = time_match.group(1).lower().replace(".", "").replace(" ", "")
            try:
                fmt = "%I:%M%p" if ":" in raw else "%I%p"
                parsed = datetime.strptime(raw, fmt)
                hour, minute = parsed.hour, parsed.minute
            except ValueError:
                pass

        return datetime.now().replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

    @staticmethod
    def _extract_price(text: str) -> str | None:
        if "free" in text.lower():
            return "Free"
        match = re.search(r"\$(\d+(?:\.\d{2})?)", text)
        if match:
            return f"${match.group(1)}"
        return None

    @staticmethod
    def _extract_venue(text: str) -> str | None:
        match = re.search(r"\bat\s+([A-Z][^,.;:(\n]{3,40})", text)
        return match.group(1).strip() if match else None
