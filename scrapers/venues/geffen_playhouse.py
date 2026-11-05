"""Geffen Playhouse — rendered performance calendar (geffenplayhouse.org/tickets/).

Markup (Nov 2026 snapshot): a month grid of
  li > h3.day-number > span.visuallyhidden  "Wednesday, November 11, 2026"
       div.calendar-super-day > h4.performance-title  "Purpose"
         a.performance-showtime[href]  "7:30PM"
Each showtime is one performance; classify.collapse_runs folds a
production's performances into one run.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as du

from ..base import Event
from ..utils.dateparse import now_utc_iso, to_la_iso
from ..utils.event_id import event_id
from ._rendered import RenderedScraper

_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([AP])M", re.I)


class Scraper(RenderedScraper):
    venue_id = "geffen_playhouse"
    events_url = "https://www.geffenplayhouse.org/tickets/"
    source_label = "geffenplayhouse.org"
    default_event_type = "performance"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for h3 in soup.select("h3.day-number"):
            day_el = h3.select_one("span.visuallyhidden")
            if not day_el:
                continue
            try:
                day = du.parse(day_el.get_text(strip=True)).date().isoformat()
            except (ValueError, OverflowError):
                continue
            # Only this day's own performance blocks (siblings of its heading).
            for block in h3.find_next_siblings("div", class_="calendar-super-day"):
                t = block.select_one("h4.performance-title")
                if not t:
                    continue
                title = t.get_text(" ", strip=True)
                for show in block.select("a.performance-showtime") or [None]:
                    start = day
                    m = _TIME.search(show.get_text(strip=True)) if show else None
                    if m:
                        h = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "P" else 0)
                        start = to_la_iso(f"{day}T{h:02d}:{int(m.group(2) or 0):02d}:00")
                    if (title, start) in seen:
                        continue
                    seen.add((title, start))
                    yield Event(
                        id=event_id(self.venue_id, start, title), venue_id=self.venue_id,
                        title=title, description="", event_type="performance",
                        start=start, end=None, all_day="T" not in start,
                        url=self.events_url, image=None,
                        source=self.source_label, scraped_at=now_utc_iso(),
                    )
