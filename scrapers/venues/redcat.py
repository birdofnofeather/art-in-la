from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "redcat"
    events_url = "https://www.redcat.org/events"
    source_label = "redcat.org"
