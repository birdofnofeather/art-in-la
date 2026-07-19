"""ESMoA (El Segundo Museum of Art) — WordPress + The Events Calendar.

The standard Tribe REST strategy works out of the box.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "esmoa"
    events_url = "https://esmoa.org/experience/"
    wp_root = "https://esmoa.org"
    source_label = "esmoa.org"
