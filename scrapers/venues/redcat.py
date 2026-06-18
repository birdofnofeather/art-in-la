"""REDCAT — Drupal site with server-rendered Tailwind event cards.

Events are in `a.event-card-stacked` elements. Each card has structured
text in the format: "date | type | type | title | artist?" all separated
by the natural text flow of the card's child elements.

The listing cards do NOT carry showtimes, so for timed events (performances,
screenings, talks, workshops) we fetch the event's detail page, which lists
the schedule as day-prefixed times — e.g. "FRI-SAT, 8 PM" or, when nights
differ, "SAT, 6 PM" / "SUN, 2 PM". Multi-night listings (a short date range
like "Jun 26 - Jun 27", or a "Jun 19, 20 & 21" day list) are expanded into
one Event per night, each at that night's showtime. Exhibitions keep their
continuous all-day date range.
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.redcat.org"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year

# Event types that have a clock time worth fetching from the detail page.
_TIMED_TYPES = {"performance", "screening", "talk", "workshop"}
# Don't expand a range longer than this into per-night events (safety: a long
# range on a timed type is more likely a series/run than discrete nights).
_MAX_EXPAND_DAYS = 8

# Maps REDCAT event type labels → our internal types
_TYPE_MAP = {
    "exhibition": "exhibition",
    "screening": "screening",
    "film": "screening",
    "theater": "performance",
    "theatre": "performance",
    "dance": "performance",
    "music": "performance",
    "talk": "talk",
    "workshop": "workshop",
}

# "Jun 19, 20 & 21" or "Jun 19 & 20" — month + list of days
_MULTI_DATE_RE = re.compile(
    r'^([A-Za-z]{3,9}\.?)\s+'    # month name
    r'(\d{1,2})'                  # first day
    r'((?:\s*[,&]\s*\d{1,2})+)'  # one or more additional days
    r'(?:\s*,?\s*(20\d\d))?$',   # optional year
    re.IGNORECASE,
)

# "8 PM", "8:00 pm", "7:30 PM"
_TIME_RE = re.compile(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', re.IGNORECASE)

# Day-prefixed showtime on a detail page: "FRI-SAT, 8 PM", "SAT, 6 PM".
_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_DAYTIME_RE = re.compile(
    r'\b(mon|tue|wed|thu|fri|sat|sun)'
    r'(?:\s*[-–—]\s*(mon|tue|wed|thu|fri|sat|sun))?'
    r'\s*,?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
    re.IGNORECASE,
)
# A "TIME 7 PM" labelled showtime (single-screening detail pages).
_LABELLED_TIME_RE = re.compile(r'\bTIME\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', re.IGNORECASE)


def _to24(hour: int, minute: int, ap: str) -> tuple[int, int]:
    ap = ap.lower()
    if ap == "pm" and hour != 12:
        hour += 12
    elif ap == "am" and hour == 12:
        hour = 0
    return hour, minute


def _parse_time_parts(parts: list[str]) -> tuple[int, int] | None:
    """Search all card text parts for a showtime; return (hour24, minute) or None."""
    for p in parts:
        m = _TIME_RE.search(p)
        if m:
            return _to24(int(m.group(1)), int(m.group(2) or 0), m.group(3))
    return None


def _flatten(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _extract_day_times(text: str) -> dict[int, tuple[int, int]]:
    """Map weekday → (hour24, minute) from day-prefixed detail-page times.

    Handles day ranges ("FRI-SAT, 8 PM" → Fri & Sat at 8 PM) and distinct
    per-night times ("SAT, 6 PM ... SUN, 2 PM"). First match for a day wins.
    """
    result: dict[int, tuple[int, int]] = {}
    for m in _DAYTIME_RE.finditer(text):
        d1 = _DAYS[m.group(1).lower()]
        d2 = _DAYS[m.group(2).lower()] if m.group(2) else d1
        hm = _to24(int(m.group(3)), int(m.group(4) or 0), m.group(5))
        day = d1
        while True:
            result.setdefault(day, hm)
            if day == d2:
                break
            day = (day + 1) % 7
    return result


def _extract_single_time(text: str) -> tuple[int, int] | None:
    """A single fallback showtime: prefer a 'TIME 7 PM' label, else first time."""
    m = _LABELLED_TIME_RE.search(text)
    if m:
        return _to24(int(m.group(1)), int(m.group(2) or 0), m.group(3))
    m = _TIME_RE.search(text)
    if m:
        return _to24(int(m.group(1)), int(m.group(2) or 0), m.group(3))
    return None


def _multidate_days(m: re.Match) -> tuple[list[date], int]:
    """From a _MULTI_DATE_RE match, return (list of dates, year)."""
    month = m.group(1)
    days = [int(m.group(2))] + [int(d) for d in re.findall(r"\d+", m.group(3))]
    year = int(m.group(4)) if m.group(4) else _CUR_YEAR
    out = []
    for day in days:
        try:
            out.append(dparser.parse(f"{month} {day} {year}",
                                     default=datetime(year, 1, 1)).date())
        except Exception:
            continue
    return out, year


def _parse_range(s: str):
    """Parse 'Apr 4 - Jul 5' or 'Apr 25' → (start_date, end_date|None, year)."""
    s = s.strip().replace("–", "-").replace("—", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            return dparser.parse(parts[0], default=default).date(), None, year
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default).date()
        end_dt = dparser.parse(end_s, default=default).date()
        return start_dt, end_dt, year
    except Exception:
        return None, None, year


def _iso_timed(d: date, hm: tuple[int, int]) -> str:
    return to_la_iso(datetime(d.year, d.month, d.day, hm[0], hm[1]))


class Scraper(BaseScraper):
    venue_id = "redcat"
    events_url = f"{BASE}/events"
    source_label = "redcat.org"

    def _detail_times(self, url: str) -> tuple[dict[int, tuple[int, int]], tuple[int, int] | None]:
        """Fetch a detail page; return (weekday→time map, single fallback time)."""
        try:
            r = get(url)
            if r and r.ok:
                txt = _flatten(r.text)
                return _extract_day_times(txt), _extract_single_time(txt)
        except Exception:
            pass
        return {}, None

    def _emit(self, **kw) -> Event:
        return Event(venue_id=self.venue_id, description="", artists=[],
                     source=self.source_label, **kw)

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.find_all("a", class_=re.compile(r"event-card"))
        for card in cards:
            href = card.get("href", "")
            url = href if href.startswith("http") else BASE + href

            # Extract structured text parts from the card
            # Typical format: "Apr 4 - Jul 5 | Exhibition | Exhibition | Title | Artist"
            parts = [t.strip() for t in card.get_text(separator="|").split("|") if t.strip()]
            if not parts:
                continue

            date_str = parts[0]
            raw_type = parts[1].lower() if len(parts) > 1 else ""
            event_type = _TYPE_MAP.get(raw_type, infer_type(raw_type, ""))

            # Title is the last substantive part (after deduplicated type labels)
            text_parts, seen = [], set()
            for p in parts[1:]:
                if p.lower() not in seen:
                    seen.add(p.lower())
                    text_parts.append(p)
            if text_parts and text_parts[0].lower() in _TYPE_MAP:
                text_parts = text_parts[1:]
            title = " — ".join(text_parts) if text_parts else ""
            if not title:
                continue

            img = card.find("img")
            image = None
            if img:
                image = img.get("src") or img.get("data-src")
                if image and image.startswith("/"):
                    image = BASE + image

            now_scraped = now_utc_iso()
            listing_time = _parse_time_parts(parts)
            is_timed = event_type in _TIMED_TYPES

            # ── Determine the set of dates this card represents ──────────────
            multi = _MULTI_DATE_RE.match(date_str.strip())
            if multi:
                dates, _ = _multidate_days(multi)
                is_continuous_range = False
            else:
                start_d, end_d, _ = _parse_range(date_str)
                if not start_d:
                    dates, is_continuous_range = [], False
                elif end_d and end_d > start_d:
                    span = (end_d - start_d).days
                    # A short range on a timed type = discrete nightly shows;
                    # anything else (exhibitions, long runs) stays continuous.
                    if is_timed and span <= _MAX_EXPAND_DAYS:
                        dates = [start_d + timedelta(days=i) for i in range(span + 1)]
                        is_continuous_range = False
                    else:
                        dates, is_continuous_range = [start_d], True
                        _end = end_d
                else:
                    dates, is_continuous_range = [start_d], False

            # ── Continuous range (exhibitions / long runs): one all-day event ─
            if is_continuous_range:
                start = to_la_iso(dates[0].isoformat(), all_day=True)
                end = to_la_iso(_end.isoformat(), all_day=True)
                yield self._emit(
                    id=event_id(self.venue_id, start, title), title=title,
                    event_type=event_type, start=start, end=end, all_day=True,
                    url=url, image=image, scraped_at=now_scraped,
                )
                continue

            if not dates:
                # Couldn't parse a date at all — emit a date-less placeholder.
                yield self._emit(
                    id=event_id(self.venue_id, None, title), title=title,
                    event_type=event_type, start=None, end=None, all_day=True,
                    url=url, image=image, scraped_at=now_scraped,
                )
                continue

            # ── Discrete dates: look up per-night showtimes when timed ───────
            day_times: dict[int, tuple[int, int]] = {}
            fallback = listing_time
            if is_timed and listing_time is None:
                day_times, detail_single = self._detail_times(url)
                fallback = fallback or detail_single

            for d in dates:
                hm = day_times.get(d.weekday(), fallback) if is_timed else None
                if hm:
                    start = _iso_timed(d, hm)
                    all_day = False
                else:
                    start = to_la_iso(d.isoformat(), all_day=True)
                    all_day = True
                yield self._emit(
                    id=event_id(self.venue_id, start, title), title=title,
                    event_type=event_type, start=start, end=None, all_day=all_day,
                    url=url, image=image, scraped_at=now_scraped,
                )
