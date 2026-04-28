"""
Self Help Graphics — stub scraper.

CMS: Squarespace

TODO: Squarespace calendar — events are loaded client-side via JS.
The ?format=json endpoint returns an empty items list.
Needs Playwright or the Squarespace events API with auth.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "self_help_graphics"
    events_url = "https://www.selfhelpgraphics.com/events-calendar"
    source_label = "selfhelpgraphics.com"

    def custom_parse(self, html, base_url):
        # JS-rendered site — no accessible server-side content.
        # Awaiting Playwright implementation.
        return []
