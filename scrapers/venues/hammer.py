from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "hammer"
    events_url = "https://hammer.ucla.edu/programs-events"
    source_label = "hammer.ucla.edu"
