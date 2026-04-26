"""Wende Museum — WordPress with The Events Calendar (Tribe) plugin."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "wende"
    events_url = "https://www.wendemuseum.org/events"
    source_label = "wendemuseum.org"
