"""Self Help Graphics is on WordPress with The Events Calendar plugin.
The plugin exposes an .ics feed at /events/?ical=1 and a JSON REST API at
/wp-json/tribe/events/v1/events. We try iCal first because it's small.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "self_help_graphics"
    events_url = "https://www.selfhelpgraphics.com/events"
    ical_url = "https://www.selfhelpgraphics.com/events/?ical=1"
    source_label = "selfhelpgraphics.com"
