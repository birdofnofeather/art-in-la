"""18th Street Arts Center — WordPress + The Events Calendar (Tribe) REST API."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "18th_street"
    events_url = "https://www.18thstreet.org/events/"
    source_label = "18thstreet.org"
    drop_exhibitions: bool = False
