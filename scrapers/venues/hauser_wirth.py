"""Hauser & Wirth uses a global exhibitions index filtered by location."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "hauser_wirth"
    events_url = "https://www.hauserwirth.com/hauser-wirth-exhibitions/?location=1160"
    source_label = "hauserwirth.com"
