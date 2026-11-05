"""LA Phil (Walt Disney Concert Hall) — rendered calendar.

Markup (laphil.com/tickets-and-events/calendar, Nov 2026 snapshot):
  div.calendar-month__item.day-2026-11-06.calendar-month__item--wdch
    p.calendar-performance__standalone-date  "Fri  Nov 6, 2026  8PM"
    h3.calendar-performance__title > a[href]  title
    p.calendar-performance__suffix            series name (optional)
    img.calendar-performance__image
The Ford (theford.com) runs on the same platform — see ford_theatres.py.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import Event
from ..utils.dateparse import now_utc_iso, to_la_iso
from ..utils.event_id import event_id
from ._rendered import RenderedScraper

_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([AP])M", re.I)


def parse_platform(html: str, venue_id: str, source: str, default_type: str) -> Iterable[Event]:
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    for item in soup.select("div.calendar-month__item"):
        day = next((c[4:] for c in item.get("class", []) if re.fullmatch(r"day-\d{4}-\d{2}-\d{2}", c)), None)
        a = item.select_one(".calendar-performance__title a[href]")
        if not day or not a:
            continue
        title = a.get_text(" ", strip=True)
        when = item.select_one(".calendar-performance__standalone-date")
        start = day
        m = _TIME.search(when.get_text(" ", strip=True).replace("\xa0", " ")) if when else None
        if m:
            h = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "P" else 0)
            start = to_la_iso(f"{day}T{h:02d}:{int(m.group(2) or 0):02d}:00")
        key = (title, start)
        if key in seen:
            continue
        seen.add(key)
        suffix = item.select_one(".calendar-performance__suffix")
        img = item.select_one("img.calendar-performance__image")
        yield Event(
            id=event_id(venue_id, start, title), venue_id=venue_id, title=title,
            description=suffix.get_text(" ", strip=True) if suffix else "",
            event_type=default_type, start=start, end=None, all_day="T" not in start,
            url=a["href"], image=img.get("src") if img else None,
            source=source, scraped_at=now_utc_iso(),
        )


class Scraper(RenderedScraper):
    venue_id = "la_phil"
    events_url = "https://www.laphil.com/tickets-and-events/calendar"
    source_label = "laphil.com"
    default_event_type = "performance"

    def custom_parse(self, html, base_url):
        yield from parse_platform(html, self.venue_id, self.source_label, self.default_event_type)
