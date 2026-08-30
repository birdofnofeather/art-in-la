"""Destination Crenshaw — outdoor public-art project along Crenshaw Boulevard.

WordPress with The Events Calendar; the base scraper's wp_tribe strategy finds
the REST feed from the site root, so no parsing code is needed here.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "destination_crenshaw"
    events_url = "https://destinationcrenshaw.la/news"
    wp_root = "https://destinationcrenshaw.la"
    source_label = "destinationcrenshaw.la"
