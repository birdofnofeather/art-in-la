"""LACMA events scraper.

LACMA's /event page is Drupal Views with `.card-event` cards -- no JSON-LD,
no WP Tribe API. We parse HTML directly and paginate via ?page=N.

Date format on page: "Sat Apr 25 | 10 am PT" (no year).
Year inference: if the parsed date is >14 days in the past, assume next year.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

import pytz
from bs4 import BeautifulSoup
from dateutil import parser as du_parser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

LA = pytz.timezone("America/Los_Angeles")
MAX_PAGES = 12


# "6 pm - 8 pm", "6:00 pm - 8:00 pm", "6pm–8pm"
_TIME_RANGE_RE = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[-–—]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)',
    re.IGNORECASE,
)
# Single time with no range: "6 pm", "10:30 am"
_SINGLE_TIME_RE = re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', re.IGNORECASE)


def _to24(h: int, m: int, ap: str) -> tuple[int, int]:
    ap = ap.lower()
    if ap == "pm" and h != 12:
        h += 12
    elif ap == "am" and h == 12:
        h = 0
    return h, m


def _parse_lacma_date(raw: str) -> tuple[str | None, str | None, bool]:
    """Parse LACMA date field -> (start_iso, end_iso, all_day).

    Handles 'Sat Apr 25 | 10 am PT' and 'Fri Jun 12 | 6 pm - 8 pm PT'.
    Times are extracted by regex so dateutil never sees them and can't bleed
    the current wall-clock minutes into the result.
    """
    if not raw:
        return None, None, False
    text = re.sub(r"\bPT\b", "", raw.replace("|", " "))
    text = re.sub(r"[–—]", "-", text)
    text = re.sub(r"\s+", " ", text).strip()

    range_m = _TIME_RANGE_RE.search(text)
    single_m = None if range_m else _SINGLE_TIME_RE.search(text)
    has_time = bool(range_m or single_m)

    # Strip times before handing text to dateutil so "6 pm - 8 pm" can't
    # be misread as a negative-day offset or similar.
    date_only = _TIME_RANGE_RE.sub("", text) if range_m else (
        _SINGLE_TIME_RE.sub("", text) if single_m else text
    )
    date_only = re.sub(r"\s*-\s*$", "", date_only)
    date_only = re.sub(r"\s+", " ", date_only).strip()

    now_la = datetime.now(LA)
    midnight = now_la.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    try:
        base = du_parser.parse(date_only, default=midnight)
        base_la = LA.localize(base.replace(tzinfo=None))
        if (now_la - base_la).days > 14:
            base_la = base_la.replace(year=base_la.year + 1)
    except Exception:
        return None, None, False

    if not has_time:
        return base_la.date().isoformat(), None, True

    if range_m:
        sh, sm = _to24(int(range_m.group(1)), int(range_m.group(2) or 0), range_m.group(3))
        eh, em = _to24(int(range_m.group(4)), int(range_m.group(5) or 0), range_m.group(6))
        start_la = base_la.replace(hour=sh, minute=sm, second=0, microsecond=0)
        end_la = base_la.replace(hour=eh, minute=em, second=0, microsecond=0)
        return start_la.isoformat(), end_la.isoformat(), False

    sh, sm = _to24(int(single_m.group(1)), int(single_m.group(2) or 0), single_m.group(3))
    start_la = base_la.replace(hour=sh, minute=sm, second=0, microsecond=0)
    return start_la.isoformat(), None, False


class Scraper(BaseScraper):
    venue_id = "lacma"
    events_url = "https://www.lacma.org/event"
    source_label = "lacma.org"

    # Disable base strategies -- this site needs custom HTML parsing
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
        seen: set[str] = set()

        for page_idx in range(MAX_PAGES):
            if page_idx == 0:
                page_html = html
            else:
                resp = get(f"{self.events_url}?page={page_idx}")
                if not resp or resp.status_code != 200:
                    break
                page_html = resp.text

            soup = BeautifulSoup(page_html, "lxml")
            cards = soup.select(".card-event")
            if not cards:
                break

            new_count = 0
            for card in cards:
                ev = self._parse_card(card)
                if ev is None or ev.id in seen:
                    continue
                seen.add(ev.id)
                new_count += 1
                yield ev

            if new_count == 0 and page_idx > 0:
                break

    def _parse_card(self, card) -> Event | None:
        name_el = card.select_one(".card-event__name a")
        if not name_el:
            return None
        title = name_el.get_text(strip=True)
        if not title:
            return None
        if re.search(r'\bmember\s+preview\b', title, re.IGNORECASE):
            return None
        link = name_el.get("href") or ""
        if link and not link.startswith("http"):
            link = "https://www.lacma.org" + link

        date_el = card.select_one(".card-event__date")
        start, end, all_day = _parse_lacma_date(
            date_el.get_text(separator=" ", strip=True) if date_el else ""
        )

        desc_el = card.select_one(".card-event__content")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        type_el = card.select_one(".card-event__type")
        type_hint = type_el.get_text(strip=True) if type_el else ""

        img_el = card.select_one(".card-event__primary_image img")
        image = img_el.get("src") if img_el else None

        loc_el = card.select_one(".card-event__location")
        location = re.sub(r"\s+", " ", loc_el.get_text(separator=" ", strip=True)).strip() if loc_el else None

        return Event(
            id=event_id(self.venue_id, start, title),
            venue_id=self.venue_id,
            title=title,
            description=desc[:800],
            event_type=infer_type(f"{title} {type_hint}", desc),
            start=start,
            end=end,
            all_day=all_day,
            url=link or None,
            image=image,
            location_override=location or None,
            source=self.source_label,
            scraped_at=now_utc_iso(),
        )
