"""Norton Simon Museum scraper.

The Norton Simon calendar at https://www.nortonsimon.org/calendar is fully
client-side rendered — the server HTML is a ~30KB shell that says
"Please wait, loading" with no event data.  Categories are at:

    /calendar/lectures
    /calendar/films-and-performances
    /calendar/special-events
    /calendar/tours-and-talks
    /calendar/family-youth-teens
    /calendar/adult-art-classes

None of these expose a public JSON/iCal/RSS API.  WordPress REST endpoints
return 404 (the WP REST API is disabled or proxied away).

TODO: Replace this stub with a Playwright-based scraper that:
  1. Navigates to each category page.
  2. Waits for `.events-program-holder` to be populated.
  3. Parses event cards (title, date, link, description).

Until then, the scraper returns an empty list so the daily run still
processes all other venues without error.
"""
from __future__ import annotations

from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "norton_simon"
    events_url = "https://www.nortonsimon.org/calendar"
    source_label = "nortonsimon.org"

    # All strategies are disabled — calendar is JS-rendered with no public API.
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    def _