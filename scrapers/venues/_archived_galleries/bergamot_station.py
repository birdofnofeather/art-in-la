"""Bergamot Station Arts Center — Squarespace Events collection.

No hand-written parsing: the base scraper's `squarespace` strategy reads the
venue's own Events collection at ?format=json, which is complete and stable.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "bergamot_station"
    events_url = "https://bergamotstation.com/exhibitions"
    source_label = "bergamotstation.com"
    default_event_type = "exhibition"
