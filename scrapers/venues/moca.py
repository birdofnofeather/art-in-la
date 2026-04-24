from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "moca_grand"
    events_url = "https://www.moca.org/events"
    source_label = "moca.org"
