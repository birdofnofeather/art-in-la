"""Morán Morán Gallery — custom site, exhibitions by year."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://moranmorangallery.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year
LA_OFFSET = "-07:00"


def _parse_range(s: str):
    s = s.strip().replace("–", "-").replace("—", "-")
    parts = re.split(r"\s*-\s*", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default, fuzzy=True)
            return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"), None
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default, fuzzy=True)
        end_dt = dparser.parse(end_s, default=default, fuzzy=True)
        return (
            start_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
            end_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
        )
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "moran_moran"
    events_url = f"{BASE}/exhibitions/{_CUR_YEAR}/"
    source_label = "moranmorangallery.com"
    drop_exhibitions = False

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
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()

        for h2 in soup.find_all("h2"):
            full_text = h2.get_text(strip=True)
            if not full_text:
                continue

            # Parent container has the full exhibition info
            container = h2.find_parent(["div", "li", "article"])
            if not container:
                continue
            container_text = container.get_text(separator="|", strip=True)

            # Extract title — the h2 may combine artist + title
            # Split on first occurrence of known exhibition title patterns
            # Usually: "Artist Name" + "Exhibition Title" concatenated in h2
            parts = container_text.split("|")
            if len(parts) < 2:
                continue

            # Try to find a date part
            date_str = ""
            for part in parts:
                if _YEAR_RE.search(part) and re.search(r"[A-Z][a-z]+\s+\d{1,2}", part):
                    date_str = part.strip()
                    break

            title = parts[0].strip()
            if not title or title in seen:
                continue
            seen.add(title)

            start, end = _parse_range(date_str) if date_str else (None, None)

            # No direct links available on listing page
            url = self.events_url

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
