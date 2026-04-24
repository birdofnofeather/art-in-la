"""Getty publishes a combined events page covering Center and Villa.

Both venues appear in the site-wide events page; we produce records for
the Getty Center only here. If you want separate Villa records, add a
second scraper with a different venue_id and the venue-specific path.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "getty_center"
    events_url = "https://www.getty.edu/visit/events/"
    source_label = "getty.edu"
