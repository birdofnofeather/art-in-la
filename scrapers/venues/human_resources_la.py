"""Human Resources Los Angeles — WordPress + The Events Calendar (Tribe) REST API."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "human_resources"
    events_url = "https://www.humanresourcesla.com/events/"
    source_label = "humanresourcesla.com"
    drop_exhibitions: bool = False
