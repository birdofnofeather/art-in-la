"""
Corita Art Center - corita.org/events
Webflow CMS site with static HTML event cards.

Rules enforced here:
  - Only yield events with an EXPLICIT time in the source.
  - Skip recurring tour/workshop series (weekly/daily standing programs).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Event, event_id
from scrapers.utils.dateparse import now_utc_iso
from scrapers.utils.warn import skip_warn

# "May 2, 2026"
_DATE_RE = re.compile(r"(\w+)\s+(\d{1,2}),\s+(\d{4})")
# "1:00pm-2:00pm" or "1:00 pm" — and Webflow sometimes renders bare 24-hour
# clock values like "14:00", so am/pm is optional and handled below.
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)?", re.IGNORECASE)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Known recurring standing programs — never one-off special events.
_RECURRING_PATTERN = re.compile(
    r"(close\s+looking|connect\s+and\s+create)",
    re.IGNORECASE,
)


def _parse_date(date_text: str):
    """Return (year, month, day) or None."""
    m = _DATE_RE.search(date_text or "")
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    return int(m.group(3)), month, int(m.group(2))


def _to_24h(hour: int, ampm: str | None) -> int:
    """12h→24h when am/pm is present; bare values are already 24-hour clock."""
    if ampm:
        if ampm.lower() == "pm" and hour != 12:
            hour += 12
        elif ampm.lower() == "am" and hour == 12:
            hour = 0
    return hour


def _parse_times(time_text: str):
    """Return (start_time, end_time) as (hour, minute) tuples; either may be None.

    Handles "1:00pm-2:00pm", "6:00pm – 7:00pm", "1:00 pm", and bare 24-hour
    values like "14:00".
    """
    matches = _TIME_RE.findall(time_text or "")
    times = []
    for h, mnt, ampm in matches[:2]:
        hour = _to_24h(int(h), ampm or None)
        minute = int(mnt)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            times.append((hour, minute))
    start = times[0] if times else None
    end = times[1] if len(times) > 1 else None
    return start, end


def _parse_datetime(date_text: str, time_text: str):
    """Return (start_dt, end_dt) — start only if BOTH a date AND an explicit
    time are found in the source; end_dt may be None."""
    ymd = _parse_date(date_text)
    if not ymd:
        return None, None
    # Require an explicit time — do not assume or default. Some cards combine
    # date+time in one block, so fall back to the date text.
    start_t, end_t = _parse_times(time_text)
    if not start_t:
        start_t, end_t = _parse_times(date_text)
    if not start_t:
        return None, None
    year, month, day = ymd
    try:
        start = datetime(year, month, day, *start_t)
        end = datetime(year, month, day, *end_t) if end_t else None
        return start, end
    except ValueError:
        return None, None


class CoritaArtCenterScraper(BaseScraper):
    venue_id = "corita_art_center"
    events_url = "https://www.corita.org/events"
    drop_exhibitions = False

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        now = datetime.now()
        seen_urls = set()
        for card in soup.find_all("a", class_="event-box"):
            href = card.get("href", "")
            url = "https://www.corita.org" + href if href.startswith("/") else href

            title_el = card.find(class_="event-page-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # Skip known recurring standing programs.
            if _RECURRING_PATTERN.search(title):
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            start_el = card.find(class_="event-page-start-date")
            time_el = card.find(class_="text-block-11")
            loc_el = card.find(class_="text-block-12")
            if not start_el:
                continue

            date_text = start_el.get_text(strip=True)
            time_text = time_el.get_text(strip=True) if time_el else ""
            start, end = _parse_datetime(date_text, time_text)
            if start is None:
                # Has a date element but no parseable time — site format may have changed.
                if _DATE_RE.search(date_text):
                    skip_warn(self.venue_id, title, "has date but no explicit time in source")
                continue
            if start < now:
                continue

            # Multi-day listings render an end date in their own element
            # (hidden via w-condition-invisible when same-day).
            end_el = card.find(class_="event-page-end-date")
            if end_el and "w-condition-invisible" not in (end_el.get("class") or []):
                end_ymd = _parse_date(end_el.get_text(strip=True))
                if end_ymd and end_ymd != (start.year, start.month, start.day):
                    et = (end.hour, end.minute) if end else (start.hour, start.minute)
                    try:
                        end = datetime(*end_ymd, *et)
                    except ValueError:
                        pass

            if "tour" in title.lower():
                etype = "tour"
            elif "workshop" in title.lower():
                etype = "workshop"
            else:
                etype = "performance"

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=None,
                event_type=etype,
                start=start,
                end=end,
                all_day=False,
                url=url,
                image=None,
                artists=[],
                location_override=loc_el.get_text(strip=True) if loc_el else None,
                source=self.events_url,
                scraped_at=now_utc_iso(),
            )
