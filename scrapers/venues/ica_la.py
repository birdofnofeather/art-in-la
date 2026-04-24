from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "ica_la"
    events_url = "https://theicala.org/en/events"
    source_label = "theicala.org"
