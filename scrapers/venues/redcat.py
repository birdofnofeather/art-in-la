"""REDCAT — Drupal site with server-rendered Tailwind event cards.

Events are in `a.event-card-stacked` elements. Each card has structured
text in the format: "date | type | type | title | artist?" all separated
by the natural text flow of the card's child elements.

Multi-night performances list all dates in one card (e.g. "Jun 19, 20 & 21")
with a shared showtime (e.g. "8 PM"). We expand these into one Event per date.
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.redcat.org"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year

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


def _parse_time_parts(parts: list[str]) -> tuple[int, int] | None:
    """Search all card text parts for a showtime; return (hour24, minute) or None."""
    for p in parts:
        m = _TIME_RE.search(p)
        if not m:
            continue
        hour, minute = int(m.group(1)), int(m.group(2) or 0)
        ap = m.group(3).lower()
        if ap == "pm" and hour != 12:
            hour += 12
        elif ap == "am" and hour == 12:
            hour = 0
        return hour, minute
    return None


def _expand_multi_dates(date_str: str, hour_min: tuple[int, int] | None) -> list[tuple[str, str | None, bool]]:
    """Return [(start_iso, end_iso, all_day), ...] for multi-date listings, or []."""
    m = _MULTI_DATE_RE.match(date_str.strip())
    if not m:
        return []

    month = m.group(1)
    first_day = int(m.group(2))
    extra_days = [int(d) for d in re.findall(r'\d+', m.group(3))]
    year_str = m.group(4)
    year = int(year_str) if year_str else _CUR_YEAR

    days = [first_day] + extra_days
    results = []
    for day in days:
        try:
            base_dt = dparser.parse(f"{month} {day} {year}", default=datetime(year, 1, 1))
        except Exception:
            continue
        if hour_min:
            dt = base_dt.replace(hour=hour_min[0], minute=hour_min[1], second=0)
            start = to_la_iso(dt)
            results.append((start, None, False))
        else:
            results.append((to_la_iso(base_dt.date().isoformat(), all_day=True), None, True))
    return results


def _parse_range(s: str):
    """Parse 'Apr 4 - Jul 5' or 'Apr 25' (year inferred as current)."""
    s = s.strip().replace("–", "-").replace("—", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default)
            return to_la_iso(dt.date().isoformat(), all_day=True), None, True
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default)
        end_dt = dparser.parse(end_s, default=default)
        return (
            to_la_iso(start_dt.date().isoformat(), all_day=True),
            to_la_iso(end_dt.date().isoformat(), all_day=True),
            True,
        )
    except Exception:
        return None, None, True


class Scraper(BaseScraper):
    venue_id = "redcat"
    events_url = f"{BASE}/events"
    source_label = "redcat.org"

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

            # First part is usually the date
            date_str = parts[0] if parts else ""
            # Event type is usually the second unique label
            raw_type = parts[1].lower() if len(parts) > 1 else ""
            event_type = _TYPE_MAP.get(raw_type, infer_type(raw_type, ""))

            # Title is the last substantive part (after deduplicated type labels)
            text_parts = []
            seen = set()
            for p in parts[1:]:
                pl = p.lower()
                if pl not in seen:
                    seen.add(pl)
                    text_parts.append(p)

            if text_parts and text_parts[0].lower() in _TYPE_MAP:
                text_parts = text_parts[1:]
            title = " — ".join(text_parts) if text_parts else ""
            if not title:
                continue

            # Image
            img = card.find("img")
            image = None
            if img:
                image = img.get("src") or img.get("data-src")
                if image and image.startswith("/"):
                    image = BASE + image

            now_scraped = now_utc_iso()

            # Try to expand multi-date listings (e.g. "Jun 19, 20 & 21 at 8 PM")
            showtime = _parse_time_parts(parts)
            expanded = _expand_multi_dates(date_str, showtime)
            if expanded:
                for start, end, all_day in expanded:
                    if not start:
                        continue
                    yield Event(
                        id=event_id(self.venue_id, start, title),
                        venue_id=self.venue_id,
                        title=title,
                        description="",
                        event_type=event_type,
                        start=start,
                        end=end,
                        all_day=all_day,
                        url=url,
                        image=image,
                        artists=[],
                        source=self.source_label,
                        scraped_at=now_scraped,
                    )
                continue

            # Single date or range
            start, end, all_day = _parse_range(date_str) if date_str else (None, None, True)
            # For single-date performances with a known showtime, apply the time
            if start and showtime and end is None and event_type in ("performance", "screening", "talk", "workshop"):
                try:
                    dt = dparser.parse(start)
                    dt = dt.replace(hour=showtime[0], minute=showtime[1], second=0)
                    start = to_la_iso(dt)
                    all_day = False
                except Exception:
                    pass

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=event_type,
                start=start,
                end=end,
                all_day=all_day,
                url=url,
                image=image,
                artists=[],
                source=self.source_label,
                scraped_at=now_scraped,
            )
