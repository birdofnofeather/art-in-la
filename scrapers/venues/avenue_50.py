"""Avenue 50 Studio — WordPress Tribe Events REST API."""
from ..base import BaseScraper
class Scraper(BaseScraper):
    venue_id = "avenue_50"
    events_url = "https://avenue50studio.org/events"
    source_label = "avenue50studio.org"
