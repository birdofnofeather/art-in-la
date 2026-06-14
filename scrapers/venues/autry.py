"""Autry Museum of the American West — Drupal HTML calendar."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

import pytz
from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://theautry.org"
LA = pytz.timezone("America/Los_Angeles")

# Handles "10–11 a.m.", "10 a.m.–12:30 p.m.", "7:00 PM - 9:30 PM"
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
_MONTH_RE = re.compile(
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2}(?:,\s*\d{4})?',
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
    """Return (start_hm, end_hm) where hm=(hour24, minute), or None."""
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


def _parse_autry_date(text: str) -> tuple[str | None, str | None, bool]:
    """Parse date + optional time from Autry date text.

    Returns (start_iso, end_iso, all_day).
    """
    # Strip times before passing to dateutil to avoid bleeding
    stripped = _TIME_RANGE_RE.sub("", _SINGLE_TIME_RE.sub("", text))
    dm = _MONTH_RE.search(stripped)
    if not dm:
        return None, None, True
    try:
        midnight = datetime(2026, 1, 1, 0, 0, 0)
        dt = dparser.parse(dm.group(0), fuzzy=True, default=midnight)
        date_str = dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None, True

    start_hm, end_hm = _parse_times(text)
    if start_hm:
        try:
            naive = datetime(dt.year, dt.month, dt.day, start_hm[0], start_hm[1])
            start_iso = LA.localize(naive).isoformat()
        except Exception:
            return None, None, True
        end_iso = None
        if end_hm:
            try:
                naive_e = datetime(dt.year, dt.month, dt.day, end_hm[0], end_hm[1])
                end_iso = LA.localize(naive_e).isoformat()
            except Exception:
                pass
        return start_iso, end_iso, False

    # No time found — emit as all-day
    return f"{date_str}T00:00:00-07:00", None, True


class Scraper(BaseScraper):
    venue_id = "autry"
    events_url = f"{BASE}/events/calendar"
    source_label = "theautry.org"

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
        # Events are article.node-type--event on /events/calendar
        articles = soup.select("article.node-type--event")
        seen: set[str] = set()
        for art in articles:
            link_el = art.find("a", href=True)
            if not link_el:
                continue
            href = link_el["href"]
            url = href if href.startswith("http") else BASE + href

            title_el = art.select_one("h3.event-title, h2.event-title, h3, h2")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or title in seen:
                continue
            seen.add(title)

            date_div = art.select_one(".autry-field-date")
            date_text = date_div.get_text(strip=True) if date_div else ""
            start, end, all_day = _parse_autry_date(date_text)
            if not start:
                start, end, all_day = _parse_autry_date(title)
            if not start:
                continue

            desc_el = art.select_one(".field--name-body, .event-description, p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            img_el = art.find("img")
            image = img_el.get("src") if img_el else None
            if image and not image.startswith("http"):
                image = BASE + image

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=all_day,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
