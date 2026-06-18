"""Clockshop — site-specific arts org, Frogtown / LA River.

clockshop.org serves a bot challenge (Altcha) to plain HTTP clients, so we
always render via headless Chromium. The events list page (/events/) has all
the data we need (title, date string, description snippet, URL), so we parse
directly from the list without fetching individual detail pages.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.render import render_pages
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://clockshop.org"
EVENTS_URL = f"{BASE}/events/"
LA_TZ = "-07:00"

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

def _parse_month_day(s: str, year: int) -> datetime | None:
    """Parse 'Month D' or 'Month DD' into a datetime (midnight)."""
    m = re.match(r"(\w+)\s+(\d{1,2})", s.strip())
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    try:
        return datetime(year, month, int(m.group(2)))
    except ValueError:
        return None

def _parse_time(t: str, meridiem: str) -> tuple[int, int] | None:
    """Parse '4', '10', '5:30' into (hour24, minute) using given meridiem."""
    t = t.strip()
    # strip any am/pm the string itself carries
    own_m = re.search(r"(am|pm)$", t, re.I)
    if own_m:
        meridiem = own_m.group(1).lower()
        t = t[: own_m.start()].strip()
    parts = t.split(":")
    try:
        h, mi = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return None
    if meridiem == "pm" and h != 12:
        h += 12
    elif meridiem == "am" and h == 12:
        h = 0
    return h, mi

def _parse_date_string(raw: str, today: datetime) -> tuple[str | None, str | None, bool]:
    """
    Parse a Clockshop date string into (start_iso, end_iso, all_day).

    Formats seen:
      "June 28, 4–6pm"          → single day with time range
      "July 11, 10am–12pm"      → single day with time range
      "September 23, 5:30–10pm" → single day with time range
      "March 13–July 10"        → multi-day / exhibition range (no times)
    """
    raw = raw.replace("–", "-").replace("—", "-").strip()
    year = today.year

    # Single day with time: "Month D, <time>"
    comma_m = re.match(r"^([A-Za-z]+ \d{1,2}),\s*(.+)$", raw)
    if comma_m:
        date_part, time_part = comma_m.group(1), comma_m.group(2)
        dt = _parse_month_day(date_part, year)
        if dt is None:
            return None, None, True
        # Guess next year if date already passed significantly
        if dt < today.replace(month=today.month) and (today - dt).days > 60:
            dt = dt.replace(year=year + 1)

        # Parse time range "4-6pm", "10am-12pm", "5:30-10pm"
        range_m = re.match(r"^(.+?)-(.+)$", time_part)
        if range_m:
            end_raw = range_m.group(2).strip()
            end_meridiem_m = re.search(r"(am|pm)$", end_raw, re.I)
            meridiem = end_meridiem_m.group(1).lower() if end_meridiem_m else "pm"

            start_parsed = _parse_time(range_m.group(1), meridiem)
            end_parsed = _parse_time(end_raw, meridiem)
            if start_parsed:
                sh, sm = start_parsed
                start_iso = f"{dt.strftime('%Y-%m-%d')}T{sh:02d}:{sm:02d}:00{LA_TZ}"
            else:
                start_iso = f"{dt.strftime('%Y-%m-%d')}T00:00:00{LA_TZ}"
            if end_parsed:
                eh, em = end_parsed
                end_iso = f"{dt.strftime('%Y-%m-%d')}T{eh:02d}:{em:02d}:00{LA_TZ}"
            else:
                end_iso = None
            return start_iso, end_iso, False

        # No time range found; treat as all-day
        return dt.strftime("%Y-%m-%d"), None, True

    # Multi-day range: "Month D-Month D" (no comma)
    range_m = re.match(r"^([A-Za-z]+ \d{1,2})\s*-\s*([A-Za-z]+ \d{1,2})$", raw)
    if range_m:
        start_dt = _parse_month_day(range_m.group(1), year)
        end_dt = _parse_month_day(range_m.group(2), year)
        if start_dt and end_dt:
            if end_dt < start_dt:
                end_dt = end_dt.replace(year=year + 1)
            return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), True
        return None, None, True

    return None, None, True


class Scraper(BaseScraper):
    venue_id = "clockshop"
    events_url = EVENTS_URL
    source_label = "clockshop.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        html = render_pages([self.events_url]).get(self.events_url)
        if not html:
            return
        yield from self._parse(html)

    def _parse(self, html: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        section = soup.find("section", class_="upcoming-events")
        if not section:
            return
        today = datetime.today()
        scraped = now_utc_iso()

        for cell in section.find_all("div", class_="grid-3"):
            title_el = cell.find("h2") or cell.find("h3")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            a_el = cell.find("a", href=True)
            url = a_el["href"] if a_el else None
            if url and not url.startswith("http"):
                url = BASE + url

            # Extract date string: the text node immediately after the h2
            # (it appears as direct text or in a <p> before the description)
            full_text = cell.get_text(separator="|", strip=True)
            parts = [p for p in full_text.split("|") if p and p != title and p != "RSVP"]
            date_raw = parts[0] if parts else ""

            # Extract description: remaining parts minus the date and RSVP
            desc = " ".join(p for p in parts[1:] if p and p != "RSVP")[:800]

            start, end, all_day = _parse_date_string(date_raw, today)

            yield Event(
                id=event_id(self.venue_id, start or title, title),
                venue_id=self.venue_id,
                title=title,
                description=desc or None,
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=all_day,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=scraped,
            )
