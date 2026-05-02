"""
Beyond Baroque / Mike Kelley Gallery - beyondbaroque.org
Static HTML homepage listing upcoming events and gallery exhibitions.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Event, event_id
from scrapers.utils.dateparse import now_utc_iso

_MONTH_ABBR = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "Friday, May 1, 2026"
_EVENT_DATE_RE = re.compile(
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),\s+"
    r"(\w+)\s+(\d{1,2}),\s+(\d{4})",
    re.IGNORECASE,
)
# "H:MM PM PT"
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*PT", re.IGNORECASE)

# "April 11 - May 9, 2026"  or  "March 28 to May 9, 2026, 2026"
_RANGE_RE = re.compile(
    r"(\w+)\s+(\d{1,2})\s*(?:[-]|to)\s*(\w+)\s+(\d{1,2}),\s*(\d{4})",
    re.IGNORECASE,
)

_TODAY = datetime.today()


def _parse_event_date(text):
    """Return datetime only if BOTH a date AND explicit time are found in the source."""
    m = _EVENT_DATE_RE.search(text)
    if not m:
        return None
    month = _MONTH_ABBR.get(m.group(1).lower())
    if not month:
        return None
    day, year = int(m.group(2)), int(m.group(3))

    # Require an explicit time — do not assume or default.
    tm = _TIME_RE.search(text)
    if not tm:
        return None  # no explicit time → skip this event

    hour, minute = int(tm.group(1)), int(tm.group(2))
    if tm.group(3).upper() == "PM" and hour != 12:
        hour += 12
    elif tm.group(3).upper() == "AM" and hour == 12:
        hour = 0
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def _parse_range(text):
    m = _RANGE_RE.search(text)
    if not m:
        return None, None
    sm = _MONTH_ABBR.get(m.group(1).lower())
    em = _MONTH_ABBR.get(m.group(3).lower())
    sd, ed, year = int(m.group(2)), int(m.group(4)), int(m.group(5))
    if not sm or not em:
        return None, None
    try:
        return datetime(year, sm, sd), datetime(year, em, ed)
    except ValueError:
        return None, None


class BeyondBaroqueScraper(BaseScraper):
    venue_id = "beyond_baroque"
    events_url = "https://beyondbaroque.org/"
    drop_exhibitions = False

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        in_events = False
        in_exhibitions = False

        for tag in soup.find_all(True):
            if tag.name in ("h2", "h3", "h4"):
                inner = tag.get_text(" ", strip=True).lower()
                if "upcoming events" in inner:
                    in_events = True
                    in_exhibitions = False
                    continue
                elif "exhibition" in inner:
                    in_events = False
                    in_exhibitions = True
                    continue
                else:
                    in_events = False
                    in_exhibitions = False
                    continue
            if tag.name == "center":
                h = tag.find(["h2", "h3", "h4"])
                if h:
                    inner = h.get_text(" ", strip=True).lower()
                    if "upcoming events" in inner:
                        in_events = True
                        in_exhibitions = False
                    elif "exhibition" in inner:
                        in_events = False
                        in_exhibitions = True
                    else:
                        in_events = False
                        in_exhibitions = False
                    continue

            if not (in_events or in_exhibitions):
                continue
            if tag.name != "p":
                continue
            if tag.get("align") != "center":
                continue

            raw = tag.get_text("\n", strip=True)
            if not raw:
                continue

            if in_events:
                strongs = tag.find_all("strong")
                if len(strongs) < 2:
                    continue
                title = strongs[0].get_text(" ", strip=True).strip().rstrip(".")
                if not title or len(title) < 3:
                    continue
                date_str = strongs[1].get_text("\n", strip=True)
                start = _parse_event_date(date_str)
                if not start or start < _TODAY:
                    continue
                a_tag = tag.find("a", href=re.compile(r"eventbrite\.com", re.I))
                url = a_tag["href"] if a_tag else self.events_url
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
                    source=self.events_url,
                    scraped_at=now_utc_iso(),
                )

            elif in_exhibitions:
                strongs = tag.find_all("strong")
                if not strongs:
                    continue
                header_text = strongs[0].get_text("\n", strip=True)
                lines = [l.strip() for l in header_text.split("\n") if l.strip()]
                if not lines:
                    continue
                title = lines[0].strip().rstrip(".")
                full_text = tag.get_text(" ", strip=True)
                start, end = _parse_range(full_text)
                if not end or end < _TODAY:
                    continue
                a_tag = tag.find("a", href=True)
                url = self.events_url
                if a_tag:
                    href = a_tag["href"]
                    if not re.search(r"eventbrite|proxygallery", href, re.I):
                        if not href.startswith("http"):
                            href = "https://beyondbaroque.org/" + href.lstrip("/")
                        url = href
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
                    source=self.events_url,
                    scraped_at=now_utc_iso(),
                )
