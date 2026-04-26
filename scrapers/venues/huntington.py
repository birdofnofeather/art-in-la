"""The Huntington Library, Art Museum, and Botanical Gardens scraper.

huntington.org is a Next.js / Vercel app whose calendar at /calendar is
fully client-side rendered.  The server HTML contains only an address
sidebar; event data loads asynchronously via internal APIs that are not
publicly accessible (Vercel bot protection + no CORS headers for scrapers).

The ticketing system (tickets.huntington.org, built by Ticketure) lists
admission products, not cultural-program events; its API returns 403 for
non-browser agents.

TODO: Replace this stub with a Playwright-based scraper that:
  1. Navigates to https://www.huntington.org/calendar
  2. Waits for event cards to render (e.g., `[class*="event-card"]`).
  3. Parses title, date/time, category, description, and link.

Until then, the scraper returns an empty list.
"""
from __future__ import annotations

from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "huntington"
    events_url = "https://www.huntington.org/calendar"
    source_label = "huntington.org"

    # Calendar is JS-rendered with no accessible public API.
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    def _strategy_custom(self): return iter([])
