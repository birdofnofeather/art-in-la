"""
Blum — stub scraper.

CMS: Bubble.io

TODO: BLUM (formerly Blum & Poe) migrated to blum-gallery.com running Bubble.io.
All content is JS-rendered with no accessible REST API.
Needs Playwright to scrape.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "blum"
    events_url = "https://blum-gallery.com/exhibitions/?lang=eng"
    source_label = "blum-gallery.com"

    def custom_parse(self, html, base_url):
        # JS-rendered site — no accessible server-side content.
        # Awaiting Playwright implementation.
        return []
