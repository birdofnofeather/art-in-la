from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "lace"
    events_url = "https://welcometolace.org/programs"
    source_label = "welcometolace.org"
