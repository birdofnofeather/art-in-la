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

_TODAY = datetime.today()

# "May 2, 2026"
_DATE_RE = re.compile(r"(\w+)\s+(\d{1,2}),\s+(\d{4})")
# "1:00pm-2:00pm" or "1:00 pm"
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)", re.IGNORECASE)

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


def _parse_datetime(date_text: str, time_text: str):
    """Return datetime only if BOTH a date AND an explicit time are found."""
    m = _DATE_RE.search(date_text)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    day, year = int(m.group(2)), int(m.group(3))

    # Require an explicit time — do not assume or default.
    tm = _TIME_RE.search(time_text)
    if not tm:
        # Also try the date text itself (some cards combine date+time).
        tm = _TIME_RE.search(date_text)
    if not tm:
        return None  # no explicit time → skip this event

    hour, minute = int(tm.group(1)), int(tm.group(2))
    if tm.group(3).lower() == "pm" and hour != 12:
        hour += 12
    elif tm.group(3).lower() == "am" and hour == 12:
        hour = 0
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


class CoritaArtCenterScraper(BaseScraper):
    venue_id = "corita_art_center"
    events_url = "https://www.corita.org/events"
    drop_exhibitions = False

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

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
            if not start_el:
                continue

            date_text = start_el.get_text(strip=True)
            time_text = time_el.get_text(strip=True) if time_el else ""
            start = _parse_datetime(date_text, time_text)
            if start is None:
                # Has a date element but no parseable time — site format may have changed.
                if _DATE_RE.search(date_text):
                    skip_warn(self.venue_id, title, "has date but no explicit time in source")
                continue
            if start < _TODAY:
                continue

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
                end=None,
                all_day=False,
                url=url,
                image=None,
                artists=[],
                location_override=None,
                source=self.events_url,
                scraped_at=now_utc_iso(),
            )
