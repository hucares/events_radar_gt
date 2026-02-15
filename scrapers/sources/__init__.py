"""Auto-import all source scrapers to trigger @register decorators."""

from scrapers.sources import (  # noqa: F401
    dice,
    eventbrite,
    meetup,
    resident_advisor,
    the_skint,
)
