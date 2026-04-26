"""Hauser & Wirth West Hollywood.

H&W's website does not currently expose a separate West Hollywood location
filter — all LA shows aggregate under "los-angeles". This stub defers to a
Playwright-based scrape once the site exposes a WeHo-specific slug.

TODO: If H&W adds a WeHo location slug (e.g. "west-hollywood"), update
events_url and custom_parse to filter by that slug. Until then this scraper
intentionally returns 0 events to avoid duplicating hauser_wirth.
"""
from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "hauser_wirth_weho"
    events_url = ""   # disabled — no separate WeHo feed available
    source_label = "hauserwirth.com"

    def custom_parse(self, html, base_url):