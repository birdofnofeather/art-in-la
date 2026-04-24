from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "the_pit"
    events_url = "https://the-pit.la/exhibitions"
    source_label = "the-pit.la"
