"""CAAM (California African American Museum).

caamuseum.org is a JS SPA with no server-rendered event data, but CAAM runs
its programs through Eventbrite. The organizer page renders only a few events
server-side, so we collect the /e/ links it does expose and read each event
page's JSON-LD (which includes offers → free/paid; CAAM programs are
generally free).
"""
from __future__ import annotations

import re
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get

ORGANIZER = "https://www.eventbrite.com/o/california-african-american-museum-13963769921"
_EVENT_LINK = re.compile(r"https://www\.eventbrite\.com/e/[a-z0-9\-]+")
_MAX_DETAIL_PAGES = 15


class Scraper(BaseScraper):
    venue_id = "caam"
    events_url = "https://caamuseum.org/programs"
    source_label = "eventbrite.com (CAAM)"

    # The generic strategies can't see the SPA — go straight to custom.
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(ORGANIZER)
        if resp is None or not resp.ok:
            return
        links = []
        for url in _EVENT_LINK.findall(resp.text):
            if url not in links:
                links.append(url)
        for url in links[:_MAX_DETAIL_PAGES]:
            yield from self._jsonld_events_from_url(url)
