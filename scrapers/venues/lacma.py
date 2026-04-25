"""LACMA's events listing is at /event (singular). It paginates one week at a
time via ?page=N. We walk up to 12 pages so a typical 2-3 month look-ahead is
covered without hammering the server. Each page contains structured event
cards in JSON-LD.
"""
from __future__ import annotations

import json
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event, _flatten_jsonld, _is_event
from ..utils.http import get


class Scraper(BaseScraper):
    venue_id = "lacma"
    events_url = "https://www.lacma.org/event"
    source_label = "lacma.org"

    MAX_PAGES = 12  # ~12 weeks of look-ahead

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        """Walk paginated pages, collecting JSON-LD events from each."""
        seen_ids = set()

        # Page 0 is what we already have (the html argument).
        for page_idx in range(self.MAX_PAGES):
            if page_idx == 0:
                page_html = html
            else:
                page_url = f"{self.events_url}?page={page_idx}"
                resp = get(page_url)
                if not resp or resp.status_code != 200:
                    break
                page_html = resp.text

            soup = BeautifulSoup(page_html, "lxml")
            new_on_page = 0
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                payload = script.string or script.text
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                for obj in _flatten_jsonld(data):
                    if not _is_event(obj):
                        continue
                    ev = self._event_from_jsonld(obj)
                    if ev.id in seen_ids:
                        continue
                    seen_ids.add(ev.id)
                    new_on_page += 1
                    yield ev

            # Stop once a page produces nothing new — likely past the end.
            if new_on_page == 0 and page_idx > 0:
                break
