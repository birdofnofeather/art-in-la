from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "lacma"
    events_url = "https://www.lacma.org/events"
    source_label = "lacma.org"
