"""Hauser & Wirth West Hollywood — shares the same global index as DTLA,
filtered by a different location ID. Adjust the location query string if
Hauser & Wirth changes it.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "hauser_wirth_weho"
    # Generic (unfiltered) URL as a fallback; the site-wide index still
    # surfaces location-tagged records we can attribute in dedup.
    events_url = "https://www.hauserwirth.com/hauser-wirth-exhibitions/"
    source_label = "hauserwirth.com"
