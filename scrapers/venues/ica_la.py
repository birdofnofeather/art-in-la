"""ICA LA — Institute of Contemporary Art, Los Angeles.

The calendar at /en/calendar is a Spree (Rails) page rendered server-side, so
the events are present in the HTML (no JS or API needed). Structure:

    .calendar__month  > .calendar__month-name        (e.g. "June")
                      > .calendar-event
                          .calendar-event__day        (e.g. "10")
                          .calendar-event__time       (e.g. "7 PM")
                          .calendar-event__title a[href]
                          .badge-calendar_category    (one or more)
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://www.theicala.org"


def _build_start(month_name: str, day: str, time_txt: str) -> Optional[str]:
    """Combine 'June' + '10' + '7 PM' into an LA-local naive ISO string.

    Year is inferred as the nearest occurrence not in the past. Returns a naive
    string; the pipeline's to_la_iso attaches the LA offset (no conversion).
    """
    if not day.isdigit():
        return None
    today = datetime.now()
    base = None
    for yr in (today.year, today.year + 1):
        try:
            cand = dparser.parse(f"{month_name} {day} {yr}")
        except (ValueError, OverflowError):
            return None
        if cand.date() >= today.date().replace(day=1):
            base = cand
            break
    if base is None:
        return None
    if time_txt:
        try:
            t = dparser.parse(time_txt)
            base = base.replace(hour=t.hour, minute=t.minute)
            return base.strftime("%Y-%m-%dT%H:%M:00")
        except (ValueError, OverflowError):
            pass
    return base.strftime("%Y-%m-%d")


class Scraper(BaseScraper):
    venue_id = "ica_la"
    events_url = f"{BASE}/en/calendar"
    source_label = "theicala.org"

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
        seen: set[str] = set()
        for month_block in soup.select(".calendar__month"):
            name_el = month_block.select_one(".calendar__month-name")
            month_name = name_el.get_text(strip=True) if name_el else ""
            if not month_name:
                continue
            for card in month_block.select(".calendar-event"):
                title_el = card.select_one(".calendar-event__title a")
                if not title_el:
                    continue
                title = title_el.get_text(" ", strip=True)
                if not title:
                    continue
                href = title_el.get("href", "")
                url = BASE + href if href.startswith("/") else href
                day_el = card.select_one(".calendar-event__day")
                time_el = card.select_one(".calendar-event__time")
                day = day_el.get_text(strip=True) if day_el else ""
                time_txt = time_el.get_text(" ", strip=True) if time_el else ""
                start = _build_start(month_name, day, time_txt)
                if not start:
                    continue
                key = (title, start)
                if key in seen:
                    continue
                seen.add(key)
                cats = " ".join(
                    b.get_text(" ", strip=True)
                    for b in card.select(".badge-calendar_category")
                )
                yield Event(
                    id=event_id(self.venue_id, start, title),
                    venue_id=self.venue_id,
                    title=title,
                    description="",
                    event_type=infer_type(title, cats),
                    start=start,
                    end=None,
                    all_day=False,
                    url=url,
                    image=None,
                    source=self.source_label,
                    scraped_at=now_utc_iso(),
                )
