"""Luckman Gallery / Luckman Fine Arts Complex at Cal State LA.

WordPress without Tribe REST, but the events category exposes a standard RSS
feed. Items are performances and gallery events; the classifier types them.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "luckman"
    events_url = "https://theluckman.org/events/"
    feed_url = "https://theluckman.org/category/events/feed/"
    source_label = "theluckman.org"
