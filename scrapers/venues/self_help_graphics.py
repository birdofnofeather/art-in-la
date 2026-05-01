"""
Self Help Graphics & Art - selfhelpgraphics.com
Squarespace site. Events render server-side in summary-v2 blocks.
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
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}

def _parse_date(text):
    m = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', text)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    try:
        return datetime(int(m.group(3)), month, int(m.group(2)))
    except ValueError:
        return None


class Scraper(BaseScraper):
    venue_id = "self_help_graphics"
    events_url = "https://www.selfhelpgraphics.com/events-calendar"
    source_label = "selfhelpgraphics.com"

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        # Squarespace Summary V2: each event card has a time.summary-metadata-item--date
        # and a .summary-title a link. Cards may repeat across multiple summary blocks.
        for time_el in soup.select("time.summary-metadata-item--date"):
            date_text = time_el.get_text(strip=True)
            start = _parse_date(date_text)
            if not start or start < _TODAY:
                continue

            # Walk up to find the summary-item container
            container = time_el.parent
            while container and "summary-item" not in " ".join(container.get("class", [])):
                container = container.parent

            if not container:
                continue

            title_a = container.select_one(".summary-title a") or container.find("a", href=True)
            if not title_a:
                continue

            title = title_a.get_text(strip=True)
            href = title_a.get("href", "")
            url = "https://www.selfhelpgraphics.com" + href if href.startswith("/") else href

            if url in seen:
                continue
            seen.add(url)

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=None,
                event_type="performance",
                start=start,
                end=None,
                all_day=True,
                url=url,
                image=None,
                artists=[],
                location_override=None,
                source=self.events_url,
                scraped_at=now_utc_iso(),
            )
