"""Marciano Art Foundation — WordPress with schema.org exhibition markup."""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://marcianoartfoundation.org"


class Scraper(BaseScraper):
    venue_id = "marciano"
    events_url = f"{BASE}/exhibitions"
    source_label = "marcianoartfoundation.org"
    drop_exhibitions = False  # we want exhibitions

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        # Each exhibition is in div.exhibition-listing__wrapper with schema.org markup
        wrappers = soup.select(".exhibition-listing__wrapper")
        for wrapper in wrappers:
            title_el = wrapper.select_one(".exhibition-listing__title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url = title_el.get("href") or ""
            if url and not url.startswith("http"):
                url = BASE + url

            # Dates via itemprop content attributes
            start_el = wrapper.find(itemprop="startDate")
            end_el = wrapper.find(itemprop="endDate")
            start = start_el.get("content") if start_el else None
            end = end_el.get("content") if end_el else None
            if start:
                start = f"{start}T00:00:00-07:00"
            if end:
                end = f"{end}T00:00:00-07:00"

            desc_el = wrapper.select_one(".exhibition-listing__summary")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            img_el = wrapper.find("img")
            image = img_el.get("src") if img_el else None

            yield Event(
                id=event_id(self.venue_id, start, title + "::exh"),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
