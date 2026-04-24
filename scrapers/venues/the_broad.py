from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "the_broad"
    events_url = "https://www.thebroad.org/events"
    source_label = "thebroad.org"
