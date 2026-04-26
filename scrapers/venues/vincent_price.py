"""Vincent Price Art Museum — WordPress with The Events Calendar (Tribe) plugin."""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "vincent_price"
    events_url = "https://vincentpriceartmuseum.org/events"
    source_label = "vincentpriceartmuseum.org"
