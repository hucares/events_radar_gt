"""Auto-import all source scrapers to trigger @register decorators."""

from scrapers.sources import (  # noqa: F401
    dice,
    edmtrain,
    eventbrite,
    meetup,
    nyc_parks,
    resident_advisor,
    the_skint,
    ticketmaster,
)
