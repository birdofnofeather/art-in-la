"""The Pit (Glendale) — stub scraper.

CMS: Squarespace

The site at the-pit.la has an SSL certificate mismatch (cert issued for
www.the-pit.la but served on the-pit.la). Content is entirely JS-rendered —
no events appear in server-side HTML. events_url is left empty to suppress
SSL errors during strategy auto-detection.

TODO: Playwright scrape of https://www.the-pit.la/current-exhibitions once
SSL is fixed or via http.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "the_pit"
    events_url = ""   # disabled — SSL cert mismatch + JS-only content
    source_label = "the-pit.la"

    def custom_parse(self, html, base_url):
        return []
