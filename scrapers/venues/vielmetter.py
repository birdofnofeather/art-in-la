from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "vielmetter"
    events_url = "https://vielmetter.com/exhibitions"
    source_label = "vielmetter.com"
