"""Abstract base scraper with httpx, rate limiting, retries, and UA rotation."""

from __future__ import annotations

import abc
import asyncio
import json
import random
from datetime import date
from pathlib import Path
from typing import Sequence

import httpx

from scrapers.models import Event

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

OUTPUT_DIR = Path(__file__).parent / "output"


class BaseScraper(abc.ABC):
    """Abstract base scraper that all source scrapers must subclass."""

    #: Unique source identifier, e.g. "eventbrite".
    name: str = ""

    #: Minimum seconds between requests.
    rate_limit: float = 1.0

    #: Maximum retry attempts per request.
    max_retries: int = 3

    #: Backoff factor for retries (seconds multiplied by attempt number).
    retry_backoff: float = 1.0

    def __init__(self) -> None:
        if not self.name:
            raise ValueError("Scraper subclass must set 'name'")
        self._client: httpx.AsyncClient | None = None
        self._last_request: float = 0.0

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": random.choice(_USER_AGENTS)},
                follow_redirects=True,
                timeout=30.0,
            )
        return self._client

    async def _rate_limit_wait(self) -> None:
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = asyncio.get_event_loop().time()

    async def fetch(self, url: str, **kwargs: object) -> httpx.Response:
        """GET *url* with rate limiting, retries, and UA rotation."""
        client = await self._ensure_client()
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            await self._rate_limit_wait()
            try:
                resp = await client.get(url, **kwargs)  # type: ignore[arg-type]
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait = self.retry_backoff * attempt
                    await asyncio.sleep(wait)
                    # Rotate UA on retry
                    client.headers["User-Agent"] = random.choice(_USER_AGENTS)
        raise RuntimeError(
            f"[{self.name}] {url} failed after {self.max_retries} attempts"
        ) from last_exc

    # ------------------------------------------------------------------
    # Scrape contract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def scrape(self) -> list[Event]:
        """Fetch and return events from this source."""

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _output_path(self) -> Path:
        return OUTPUT_DIR / f"{self.name}_{date.today().isoformat()}.json"

    async def run(self) -> list[Event]:
        """Execute scrape, persist results to JSON, and return events."""
        try:
            events = await self.scrape()
        finally:
            if self._client and not self._client.is_closed:
                await self._client.aclose()

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = self._output_path()
        out.write_text(
            json.dumps(
                [e.model_dump(mode="json") for e in events],
                indent=2,
            ),
            encoding="utf-8",
        )
        return events


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

_registry: dict[str, type[BaseScraper]] = {}


def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    """Class decorator that registers a scraper by its *name*."""
    _registry[cls.name] = cls
    return cls


def get_scrapers() -> dict[str, type[BaseScraper]]:
    """Return a copy of the scraper registry."""
    return dict(_registry)


def get_scraper(name: str) -> type[BaseScraper]:
    """Look up a registered scraper by name."""
    try:
        return _registry[name]
    except KeyError:
        raise KeyError(f"Unknown scraper: {name!r}. Available: {list(_registry)}")


async def run_all(sources: Sequence[str] | None = None) -> list[Event]:
    """Run scrapers (all or a subset) and return combined events."""
    registry = get_scrapers()
    names = list(sources) if sources else list(registry)
    all_events: list[Event] = []
    for name in names:
        scraper = get_scraper(name)()
        events = await scraper.run()
        all_events.extend(events)
    return all_events
