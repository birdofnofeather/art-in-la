"""
LA Plaza de Cultura y Artes - lapca.org
WordPress site with custom exhibitions and programs list widgets.

Rules enforced here:
  - Programs (one-off events): only yield if an explicit time is in the source.
  - Exhibitions (all_day=True): date range only, no time required.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Event, event_id
from scrapers.utils.dateparse import now_utc_iso

_TODAY = datetime.today()

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "May 2, 2026" or "June 28, 2025"
_DATE_RE = re.compile(r"(\w+)\s+(\d{1,2}),\s+(\d{4})")
# "6:00 pm" or "12:00 pm"
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)", re.IGNORECASE)
# "June 28, 2025-August 23, 2026" for exhibitions
_RANGE_RE = re.compile(
    r"(\w+)\s+(\d{1,2}),\s+(\d{4})\s*[-–]\s*(\w+)\s+(\d{1,2}),\s+(\d{4})"
)


def _parse_date(text, time_text="", require_time=False):
    """Return datetime only if a date is found; require explicit time when require_time=True."""
    m = _DATE_RE.search(text)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    day, year = int(m.group(2)), int(m.group(3))

    tm = _TIME_RE.search(time_text) if time_text else None
    if not tm:
        tm = _TIME_RE.search(text)
    if require_time and not tm:
        return None  # no explicit time in source → skip this event

    hour, minute = 0, 0
    if tm:
        hour, minute = int(tm.group(1)), int(tm.group(2))
        if tm.group(3).lower() == "pm" and hour != 12:
            hour += 12
        elif tm.group(3).lower() == "am" and hour == 12:
            hour = 0
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def _parse_range(text):
    m = _RANGE_RE.search(text)
    if not m:
        return None, None
    sm = _MONTHS.get(m.group(1).lower())
    em = _MONTHS.get(m.group(4).lower())
    if not sm or not em:
        return None, None
    try:
        start = datetime(int(m.group(3)), sm, int(m.group(2)))
        end = datetime(int(m.group(6)), em, int(m.group(5)))
        return start, end
    except ValueError:
        return None, None


class LaPlazaScraper(BaseScraper):
    venue_id = "la_plaza"
    drop_exhibitions = False

    def _strategy_custom(self):
        from scrapers.utils.http import get

        # --- Exhibitions ---
        resp = get("https://lapca.org/exhibitions/")
        if resp and resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            seen = set()
            for card in soup.find_all(class_=re.compile(r"\bexhibition\b")):
                a = card.find("a", href=re.compile(r"lapca\.org/exhibition/"))
                if not a:
                    continue
                url = a["href"]
                title_el = card.find(["h2", "h3", "h4"])
                if not title_el:
                    title_el = a
                title = title_el.get_text(strip=True)
                if not title or title in seen:
                    continue
                text = card.get_text(" ", strip=True)
                if "Permanent" in text:
                    continue
                seen.add(title)
                start, end = _parse_range(text)
                if not end or end < _TODAY:
                    continue
                yield Event(
                    id=event_id(self.venue_id, start or _TODAY, title),
                    venue_id=self.venue_id,
                    title=title,
                    description=None,
                    event_type="exhibition",
                    start=start or _TODAY,
                    end=end,
                    all_day=True,
                    url=url,
                    image=None,
                    artists=[],
                    location_override=None,
                    source="https://lapca.org/exhibitions/",
                    scraped_at=now_utc_iso(),
                )

        # --- Upcoming programs ---
        resp = get("https://lapca.org/upcoming-programs/")
        if resp and resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            seen_urls = set()
            for item in soup.find_all("li", class_="event-list-item"):
                a = item.find("a", href=re.compile(r"lapca\.org/event"))
                if not a:
                    continue
                url = a["href"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title_el = item.find("h3") or item.find("h2")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # Date is in a <div> inside meta-data
                meta = item.find(class_="meta-data alt")
                date_text = ""
                time_text = ""
                if meta:
                    divs = meta.find_all("div", recursive=False)
                    # divs[0] = venue, divs[1] = date, divs[2] = time
                    if len(divs) > 1:
                        date_text = divs[1].get_text(strip=True)
                    if len(divs) > 2:
                        time_text = divs[2].get_text(strip=True)
                if not date_text:
                    date_text = item.get_text(" ", strip=True)

                # Require an explicit time — skip programs listed date-only.
                start = _parse_date(date_text, time_text, require_time=True)
                if not start or start < _TODAY:
                    continue

                yield Event(
                    id=event_id(self.venue_id, start, title),
                    venue_id=self.venue_id,
                    title=title,
                    description=None,
                    event_type="performance",
                    start=start,
                    end=None,
                    all_day=False,
                    url=url,
                    image=None,
                    artists=[],
                    location_override=None,
                    source="https://lapca.org/upcoming-programs/",
                    scraped_at=now_utc_iso(),
                )
