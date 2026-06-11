"""Academy Museum of Motion Pictures — Next.js/Contentful site.

Programs are embedded in __NEXT_DATA__ as cfProgramsKeyedByTkId on the
listing page, giving us slugs and date spans. Showtimes and multi-date
session breakdowns are only on the individual detail pages, so we fetch
those for event-like programs (span ≤ 90 days) and parse time/date info
from the rendered HTML and the full Contentful program object.

For exhibitions (span > 90 days) we keep the all-day date-range approach.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso
import pytz

BASE = "https://www.academymuseum.org"
LA = pytz.timezone("America/Los_Angeles")

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)

# Max span (days) for which we bother fetching detail pages to get showtimes.
# Programs longer than this are treated as exhibitions (all-day date range).
_EVENT_SPAN_DAYS = 90


# ── time-pattern helpers ──────────────────────────────────────────────────────

# Handles "12:30–2:30pm", "7 p.m.", "10 a.m.–12:30 p.m.", "7:00 PM - 9:30 PM"
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


def _parse_times(text: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Return (start_hm, end_hm) where hm = (hour24, minute), or None."""
    m = _TIME_RANGE_RE.search(text)
    if m:
        end_ap = m.group(6)
        start_ap = m.group(3) or end_ap  # inherit end am/pm when start lacks one
        sh, sm = _to24(int(m.group(1)), int(m.group(2) or 0), start_ap)
        eh, em = _to24(int(m.group(4)), int(m.group(5) or 0), end_ap)
        return (sh, sm), (eh, em)
    m = _SINGLE_TIME_RE.search(text)
    if m:
        sh, sm = _to24(int(m.group(1)), int(m.group(2) or 0), m.group(3))
        return (sh, sm), None
    return None, None


# ── multi-date helpers ────────────────────────────────────────────────────────

# "Saturdays June 13 and 20", "June 13 and 20", "June 13 & 20"
_MULTI_DATE_RE = re.compile(
    r'(?:Saturdays?\s+|Sundays?\s+|Fridays?\s+|Thursdays?\s+|'
    r'Wednesdays?\s+|Tuesdays?\s+|Mondays?\s+)?'
    r'([A-Za-z]+)\s+(\d{1,2})'
    r'(?:\s*(?:,|and|&)\s*(\d{1,2}))+'
    r'(?:\s*(?:,|and|&)\s*(\d{1,2}))*',
    re.IGNORECASE,
)


def _expand_dates(text: str, year: int) -> list[str]:
    """Extract all dates from 'June 13 and 20' style text → ['2026-06-13', '2026-06-20']."""
    m = _MULTI_DATE_RE.search(text)
    if not m:
        return []
    month_name = m.group(1)
    full_match = m.group(0)
    # Collect all day numbers mentioned after the month
    days = [int(d) for d in re.findall(r'\d+', full_match.split(month_name, 1)[1])]
    if len(days) < 2:
        return []
    result = []
    for day in days:
        try:
            d = dparser.parse(f"{month_name} {day} {year}", default=__import__('datetime').datetime(year, 1, 1))
            result.append(d.strftime("%Y-%m-%d"))
        except Exception:
            pass
    return result


# ── rich-text helpers ─────────────────────────────────────────────────────────

def _rich_text_to_str(rt_field: dict | None) -> str:
    if not rt_field:
        return ""
    try:
        content = rt_field.get("json", {}).get("content", [])
        parts = []
        for block in content:
            for node in block.get("content", []):
                v = node.get("value", "")
                if v:
                    parts.append(v)
        return "".join(parts).strip()
    except Exception:
        return ""


def _extract_all_text(prog: dict) -> str:
    """Collect all string and rich-text content from a program object."""
    parts = []
    skip = {"__typename", "sys", "slug", "image", "imageAltText"}
    for key, val in prog.items():
        if key in skip:
            continue
        if isinstance(val, str) and len(val) < 5000:
            parts.append(val)
        elif isinstance(val, dict):
            parts.append(_rich_text_to_str(val))
    return " ".join(p for p in parts if p)


# ── detail-page fetch ─────────────────────────────────────────────────────────

def _fetch_detail(slug: str) -> tuple[dict, str]:
    """Fetch detail page; return (full cfProgram dict, visible page text)."""
    url = f"{BASE}/en/programs/detail/{slug}"
    resp = get(url)
    if not resp or not resp.ok:
        return {}, ""
    html = resp.text
    prog = {}
    m = _NEXT_DATA_RE.search(html)
    if m:
        try:
            nd = json.loads(m.group(1))
            pp = nd.get("props", {}).get("pageProps", {})
            prog = pp.get("cfProgram", pp.get("program", {}))
        except Exception:
            pass
    # Also extract visible text for "Time: ..." patterns
    soup = BeautifulSoup(html, "lxml")
    # Focus on the main content area; skip nav/header/footer noise
    main = soup.find("main") or soup.body or soup
    visible = main.get_text(" ", strip=True) if main else ""
    return prog, visible


# ── date arithmetic ───────────────────────────────────────────────────────────

def _span_days(start_raw: str, end_raw: str) -> int:
    try:
        s = date.fromisoformat(start_raw)
        e = date.fromisoformat(end_raw)
        return (e - s).days
    except Exception:
        return 0


def _make_event(venue_id, title, url, image, start_date: str,
                start_hm, end_hm, source_label, now_iso, event_type) -> Event:
    """Build an Event for a specific date + optional start/end time."""
    if start_hm:
        try:
            base = date.fromisoformat(start_date)
            from datetime import datetime as _dt
            naive = _dt(base.year, base.month, base.day, start_hm[0], start_hm[1])
            start_iso = LA.localize(naive).isoformat()
        except Exception:
            start_iso = to_la_iso(start_date, all_day=True)
            start_hm = None
        if end_hm and start_hm:
            try:
                base = date.fromisoformat(start_date)
                from datetime import datetime as _dt
                naive_e = _dt(base.year, base.month, base.day, end_hm[0], end_hm[1])
                end_iso = LA.localize(naive_e).isoformat()
            except Exception:
                end_iso = None
        else:
            end_iso = None
        all_day = False
    else:
        start_iso = to_la_iso(start_date, all_day=True)
        end_iso = None
        all_day = True

    return Event(
        id=event_id(venue_id, start_iso, title),
        venue_id=venue_id,
        title=title,
        description="",
        event_type=event_type,
        start=start_iso,
        end=end_iso,
        all_day=all_day,
        url=url,
        image=image,
        source=source_label,
        scraped_at=now_iso,
    )


class Scraper(BaseScraper):
    venue_id = "academy_museum"
    events_url = f"{BASE}/en/programs"
    source_label = "academymuseum.org"

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
        m = _NEXT_DATA_RE.search(html)
        if not m:
            return
        try:
            nd = json.loads(m.group(1))
        except Exception:
            return

        programs = nd.get("props", {}).get("pageProps", {}).get(
            "cfProgramsKeyedByTkId", {}
        )
        seen: set[str] = set()
        now_iso = now_utc_iso()

        for prog in programs.values():
            if prog.get("hideFromCalendar"):
                continue

            title = _rich_text_to_str(prog.get("programTitle"))
            if not title:
                title = _rich_text_to_str(prog.get("title"))
            if not title or title in seen:
                continue
            seen.add(title)

            slug = prog.get("slug", "")
            url = f"{BASE}/en/programs/detail/{slug}" if slug else self.events_url

            start_raw = (prog.get("activeStartDate") or "")[:10] or None
            end_raw = (prog.get("activeEndDate") or "")[:10] or None
            if not start_raw:
                continue

            image_data = prog.get("image")
            image = None
            if isinstance(image_data, dict):
                image = image_data.get("url")

            span = _span_days(start_raw, end_raw or start_raw)
            etype = infer_type(title, "")

            # Long-running exhibitions: all-day date range, no detail fetch.
            if span > _EVENT_SPAN_DAYS:
                start = to_la_iso(start_raw, all_day=True)
                end = (
                    to_la_iso(end_raw, all_day=True)
                    if end_raw and end_raw != start_raw
                    else None
                )
                yield Event(
                    id=event_id(self.venue_id, start, title),
                    venue_id=self.venue_id,
                    title=title,
                    description="",
                    event_type=etype,
                    start=start,
                    end=end,
                    all_day=True,
                    url=url,
                    image=image,
                    source=self.source_label,
                    scraped_at=now_iso,
                )
                continue

            # Short-span events: fetch detail page to get showtime and
            # any multi-date session breakdown.
            listing_text = _extract_all_text(prog)
            start_hm, end_hm = _parse_times(listing_text)
            session_dates: list[str] = []

            if not start_hm and slug:
                detail_prog, page_text = _fetch_detail(slug)
                detail_text = _extract_all_text(detail_prog) + " " + page_text
                start_hm, end_hm = _parse_times(detail_text)
                # Try to find multi-date session list in the detail text
                try:
                    year = int(start_raw[:4])
                except Exception:
                    year = 2026
                session_dates = _expand_dates(detail_text, year)
            else:
                try:
                    year = int(start_raw[:4])
                except Exception:
                    year = 2026
                session_dates = _expand_dates(listing_text, year)

            # Filter session dates to only those within the program's date span
            if session_dates and end_raw:
                try:
                    s_date = date.fromisoformat(start_raw)
                    e_date = date.fromisoformat(end_raw)
                    session_dates = [
                        d for d in session_dates
                        if s_date <= date.fromisoformat(d) <= e_date
                    ]
                except Exception:
                    pass

            if session_dates:
                # Emit one event per session date
                for sd in session_dates:
                    ev = _make_event(
                        self.venue_id, title, url, image,
                        sd, start_hm, end_hm,
                        self.source_label, now_iso, etype,
                    )
                    yield ev
            else:
                # Single date (or no session breakdown found)
                yield _make_event(
                    self.venue_id, title, url, image,
                    start_raw, start_hm, end_hm,
                    self.source_label, now_iso, etype,
                )
