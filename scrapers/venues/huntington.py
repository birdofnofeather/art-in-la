"""The Huntington — Next.js calendar behind Vercel's Security Checkpoint.

huntington.org/calendar returns HTTP 429 ("Vercel Security Checkpoint") to
plain clients and even to a headless browser on first paint — but the
checkpoint runs a proof-of-work in the page and self-clears after a couple of
seconds, after which the real calendar renders. `scrapers.utils.render` waits
the checkpoint out and hands us the populated HTML.

Calendar cards look like:

    <article class="…calendar-item-card…">
      <div class="…event-type…">Event</div>
      <a class="…title…" href="/event/slug">Title</a>
      … "June 13, 2026, 10 a.m.–12:30 p.m." … description …
    </article>

Cards carry both a date (or date range) and — for timed events — a time range
in "10 a.m.–12:30 p.m." form. We parse both when present.
"""
from __future__ import annotations

import dataclasses
import re
from datetime import datetime
from typing import Iterable

import pytz
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..base import BaseScraper, Event
from ..utils.render import render_pages
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.huntington.org"
LA = pytz.timezone("America/Los_Angeles")

# A single date like "June 13, 2026" or abbreviated "Dec. 15, 2026".
_DATE = r"[A-Z][a-z]{2,8}\.?\s+\d{1,2},\s+\d{4}"
_RANGE_RE = re.compile(rf"({_DATE})\s*[–—-]\s*({_DATE})")
_SINGLE_RE = re.compile(rf"({_DATE})")
# Noise that sits between the title and the date in the card text.
_NOISE_RE = re.compile(r"\b(Sold Out|New|Members Only|Free)\b", re.IGNORECASE)

# "10 a.m.–12:30 p.m.", "10am-12:30pm", "7:00 PM - 9:30 PM"
_AMPM = r'[ap]\.?m\.?'
_TIME_RANGE_RE = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*(?:(' + _AMPM + r')\s*)?'
    r'[–—-]\s*'
    r'(\d{1,2})(?::(\d{2}))?\s*(' + _AMPM + r')',
    re.IGNORECASE,
)
_SINGLE_TIME_RE = re.compile(
    r'\b(\d{1,2})(?::(\d{2}))?\s*(' + _AMPM + r')',
    re.IGNORECASE,
)


def _to24(h: int, m: int, ap: str) -> tuple[int, int]:
    ap = ap.lower().replace(".", "")
    if ap.startswith("p") and h != 12:
        h += 12
    elif ap.startswith("a") and h == 12:
        h = 0
    return h, m


def _to_iso(date_text: str) -> str | None:
    try:
        dt = dateparser.parse(date_text.replace(".", ""), fuzzy=True)
    except (ValueError, OverflowError):
        return None
    return to_la_iso(dt.date().isoformat(), all_day=True) if dt else None


def _to_iso_timed(date_text: str, hour: int, minute: int) -> str | None:
    try:
        dt = dateparser.parse(date_text.replace(".", ""), fuzzy=True)
    except (ValueError, OverflowError):
        return None
    if not dt:
        return None
    naive = datetime(dt.year, dt.month, dt.day, hour, minute)
    return LA.localize(naive).isoformat()


def _parse_time(text: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Return (start_hm, end_hm) or (None, None). hm = (hour24, minute)."""
    m = _TIME_RANGE_RE.search(text)
    if m:
        end_ap = m.group(6)
        start_ap = m.group(3) or end_ap
        sh, sm = _to24(int(m.group(1)), int(m.group(2) or 0), start_ap)
        eh, em = _to24(int(m.group(4)), int(m.group(5) or 0), end_ap)
        return (sh, sm), (eh, em)
    m = _SINGLE_TIME_RE.search(text)
    if m:
        sh, sm = _to24(int(m.group(1)), int(m.group(2) or 0), m.group(3))
        return (sh, sm), None
    return None, None


def _date_anchors(date_iso: str) -> list[str]:
    """Spelled-out forms of a YYYY-MM-DD date to locate it in page text."""
    try:
        d = datetime.strptime(date_iso[:10], "%Y-%m-%d")
    except ValueError:
        return []
    return [f"{d.strftime('%B')} {d.day}", f"{d.strftime('%b')} {d.day}"]


def _anchored_time(text: str, date_iso: str):
    """Find a showtime that sits right after the event's own date in `text`.

    Anchoring on the event date keeps us from grabbing unrelated times on the
    page (museum/café hours), which never appear next to the event date.
    """
    if not text:
        return None, None
    for anchor in _date_anchors(date_iso):
        idx = text.find(anchor)
        while idx != -1:
            start_hm, end_hm = _parse_time(text[idx:idx + 64])
            if start_hm:
                return start_hm, end_hm
            idx = text.find(anchor, idx + 1)
    return None, None


def _timed_from_iso(date_iso: str, hm: tuple[int, int]) -> str:
    d = datetime.strptime(date_iso[:10], "%Y-%m-%d")
    return LA.localize(datetime(d.year, d.month, d.day, hm[0], hm[1])).isoformat()


class Scraper(BaseScraper):
    venue_id = "huntington"
    events_url = f"{BASE}/calendar"
    source_label = "huntington.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        html = render_pages([self.events_url]).get(self.events_url)
        if not html:
            print(f"  [{self.venue_id}] render returned no HTML (checkpoint not cleared)")
            return
        events = list(self._parse(html))
        yield from self._recover_times(events)

    def _recover_times(self, events: list[Event]) -> Iterable[Event]:
        """Second pass: render detail pages to recover showtimes for single-date
        timeless events. Falls back to the all-day event on any failure."""
        need = [
            e for e in events
            if e.all_day and e.event_type != "exhibition" and e.url
            and (not e.end or e.end[:10] == e.start[:10])
        ]
        rendered: dict[str, str] = {}
        if need:
            urls = sorted({e.url for e in need})
            pages = render_pages(urls, timeout=min(600, 90 + 18 * len(urls)))
            for u, h in pages.items():
                if h:
                    rendered[u] = BeautifulSoup(h, "lxml").get_text(" ", strip=True)
            print(f"  [{self.venue_id}] detail render: {len(rendered)}/{len(urls)} pages for showtimes")

        for e in events:
            txt = rendered.get(e.url) if (e.all_day and e.event_type != "exhibition") else None
            if txt:
                start_hm, end_hm = _anchored_time(txt, e.start)
                if start_hm:
                    start = _timed_from_iso(e.start, start_hm)
                    end = _timed_from_iso(e.start, end_hm) if end_hm else None
                    e = dataclasses.replace(
                        e, start=start, end=end, all_day=False,
                        id=event_id(self.venue_id, start, e.title),
                    )
            yield e

    def _parse(self, html: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        now_iso = now_utc_iso()
        cards = soup.select('article[class*="calendar-item-card"]')
        seen: set[str] = set()
        for card in cards:
            title_a = card.select_one('a[class*="title"]')
            if not title_a:
                continue
            title = title_a.get_text(strip=True)
            href = title_a.get("href")
            if not title or not href:
                continue
            url = (BASE + href) if href.startswith("/") else href

            type_el = card.select_one('[class*="event-type"]')
            type_label = type_el.get_text(strip=True) if type_el else ""

            # Pull the date(s) out of the card's text. Strip the title first so a
            # date embedded in a title can't be mistaken for the event date.
            text = card.get_text(" ", strip=True)
            text = text.replace(title, " ")
            text = _NOISE_RE.sub(" ", text)

            start_hm, end_hm = _parse_time(text)

            start = end = None
            date_m = _RANGE_RE.search(text)
            if date_m:
                date1, date2 = date_m.group(1), date_m.group(2)
                if start_hm:
                    start = _to_iso_timed(date1, *start_hm)
                    end = _to_iso_timed(date2, *(end_hm or start_hm))
                else:
                    start = _to_iso(date1)
                    end = _to_iso(date2)
            else:
                date_m = _SINGLE_RE.search(text)
                if date_m:
                    date1 = date_m.group(1)
                    if start_hm:
                        start = _to_iso_timed(date1, *start_hm)
                        end = _to_iso_timed(date1, *(end_hm or start_hm)) if end_hm else None
                    else:
                        start = _to_iso(date1)
            if not start:
                continue

            all_day = start_hm is None

            img = card.find("img")
            image = img.get("src") if img else None
            if image and image.startswith("/"):
                image = BASE + image

            if type_label.lower() == "exhibition":
                etype = "exhibition"
            else:
                etype = infer_type(title, default="other")

            ev_id = event_id(self.venue_id, start, title)
            if ev_id in seen:
                continue
            seen.add(ev_id)

            yield Event(
                id=ev_id,
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=etype,
                start=start,
                end=end,
                all_day=all_day,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_iso,
            )
