"""The Ford (theford.com) — same calendar platform as the LA Phil."""
from ._rendered import RenderedScraper
from .la_phil import parse_platform


class Scraper(RenderedScraper):
    venue_id = "ford_theatres"
    events_url = "https://www.theford.com/tickets-and-events/calendar"
    source_label = "theford.com"
    default_event_type = "performance"

    def custom_parse(self, html, base_url):
        yield from parse_platform(html, self.venue_id, self.source_label, self.default_event_type)
