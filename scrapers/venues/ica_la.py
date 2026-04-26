"""
Ica La — stub scraper.

CMS: Economy CMS (custom Ruby on Rails)

TODO: All content is JS-rendered via React. No public API or iCal feed detected.
Needs Playwright headless browser to extract events.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "ica_la"
    events_url = "https://theicala.org/en/events"
    source_label = "theicala.org"

    def custom_parse(self, html, base_url):
        # JS-rendered site — no accessible server-side content.
        # Awaiting Playwright implementation.