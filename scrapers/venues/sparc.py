"""SPARC (Social and Public Art Resource Center) – Tribe Events calendar."""
from __future__ import annotations
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "sparc"
    events_url = "https://sparcinla.org/calendar/"
    source_label = "sparcinla.org"
