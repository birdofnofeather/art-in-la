"""Palos Verdes Art Center — WordPress with The Events Calendar (Tribe) plugin."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "pvac"
    events_url = "https://pvartcenter.org/events"
    source_label = "pvartcenter.org"
