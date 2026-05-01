"""
Corita Art Center - corita.org/events
Webflow CMS site with static HTML event cards.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Event, event_id
from scrapers.utils.dateparse import now_utc_iso

_TODAY = datetime.today()

# "May 2, 2026"
_DATE_RE = re.compile(r"(\w+)\s+(\d{1,2}),\s+(\d{4})")
# "1:00pm-2:00pm" or "1:00pm"
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})(am|pm)", re.IGNORECASE)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(text, time_text=""):
    m = _DATE_RE.search(text)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    day, year = int(m.group(2)), int(m.group(3))
    hour, minute = 10, 0  # default 10am for tours/workshops
    tm = _TIME_RE.search(time_text or text)
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


class CoritaArtCenterScraper(BaseScraper):
    venue_id = "corita_art_center"
    events_url = "https://www.corita.org/events"
    drop_exhibitions = False

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        # Each event card is an <a class="event-box ...">
        seen = set()
        for card in soup.find_all("a", class_="event-box"):
            href = card.get("href", "")
            url = "https://www.corita.org" + href if href.startswith("/") else href

            title_el = card.find(class_="event-page-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or url in seen:
                continue
            seen.add(url)

            start_el = card.find(class_="event-page-start-date")
            time_el = card.find(class_="text-block-11")
            if not start_el:
                continue

            start = _parse_date(
                start_el.get_text(strip=True),
                time_el.get_text(strip=True) if time_el else ""
            )
            if not start or start < _TODAY:
                continue

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=None,
                event_type="tour" if "tour" in title.lower() else "workshop" if "workshop" in title.lower() else "performance",
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
