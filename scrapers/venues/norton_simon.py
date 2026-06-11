"""Norton Simon Museum — JS-rendered calendar behind Cloudflare.

The calendar at https://www.nortonsimon.org/calendar is a client-side app, and
Cloudflare serves an event-less shell to plain HTTP clients. A real (headless)
browser gets the full page, so this scraper renders each category page via
`scrapers.utils.render` and parses the `.event-item` cards.

Each card looks like:

    <div class="event-item grid">
      <time class="time" datetime="2026-06-13">Saturday, June 13
        <span>1:00 pm–2:00 pm</span></time>
      <div class="img-holder"><a href="/calendar/…"><img alt="…"></a>
        <span class="tag-item">Tour</span></div>
      <div class="event-detail-text">
        <h2 class="category-heading"><a href="/calendar/…">Title</a></h2></div>
    </div>
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
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.nortonsimon.org"

# category slug -> (events_url suffix, default event_type)
_CATEGORIES = {
    "lectures": "lecture",
    "films-and-performances": "screening",
    "special-events": "other",
    "tours-and-talks": "tour",
    "family-youth-teens": "workshop",
    "adult-art-classes": "workshop",
}

# "1:00 pm" / "10:30 am"
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)", re.IGNORECASE)


def _parse_time(text: str):
    """Return (hour, minute) from the first am/pm time in `text`, or None."""
    m = _TIME_RE.search(text or "")
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    ap = m.group(3).lower()
    if ap == "pm" and hour != 12:
        hour += 12
    elif ap == "am" and hour == 12:
        hour = 0
    return hour, minute


class Scraper(BaseScraper):
    venue_id = "norton_simon"
    events_url = f"{BASE}/calendar"
    source_label = "nortonsimon.org"

    # Calendar has no public API; everything comes through the rendered DOM.
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        urls = [f"{self.events_url}/{slug}" for slug in _CATEGORIES]
        rendered = render_pages(urls)
        any_html = False
        for slug, default_type in _CATEGORIES.items():
            html = rendered.get(f"{self.events_url}/{slug}")
            if not html:
                continue
            any_html = True
            yield from self._parse_category(html, default_type)
        if not any_html:
            print(f"  [{self.venue_id}] render returned no HTML (browser unavailable or blocked)")

    def _parse_category(self, html: str, default_type: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        now = datetime.now()
        for item in soup.select(".event-item"):
            time_el = item.find("time")
            if not time_el:
                continue
            date_str = (time_el.get("datetime") or "").strip()  # "2026-06-13"
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                continue

            span = time_el.find("span")
            time_text = span.get_text(" ", strip=True) if span else ""
            times = _TIME_RE.findall(time_text)
            start_t = _parse_time(time_text)

            heading = item.select_one(".category-heading a, h2 a, h3 a")
            title = heading.get_text(strip=True) if heading else None
            if not title:
                continue

            href = heading.get("href") if heading else None
            if not href:
                link = item.find("a", href=True)
                href = link["href"] if link else None
            url = (BASE + href) if href and href.startswith("/") else href

            tag = item.select_one(".tag-item")
            tag_text = tag.get_text(strip=True) if tag else ""

            img = item.find("img")
            image = img.get("src") if img else None
            if image and image.startswith("/"):
                image = BASE + image

            # Build start / end datetimes. Time is optional — fall back to a
            # date-only listing (never fabricate a midnight time).
            if start_t:
                start = to_la_iso(datetime(*map(int, date_str.split("-")), *start_t))
                end = None
                if len(times) > 1:
                    end_t = _parse_time(f"{times[1][0]}:{times[1][1]} {times[1][2]}")
                    if end_t:
                        end = to_la_iso(datetime(*map(int, date_str.split("-")), *end_t))
            else:
                start = to_la_iso(date_str, all_day=True)
                end = None

            etype = infer_type(title, tag_text, default=default_type)

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=etype,
                start=start,
                end=end,
                all_day=not bool(start_t),
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
