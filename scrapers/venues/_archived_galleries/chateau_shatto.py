"""Château Shatto — custom Next.js site with structured exhibition links."""
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

BASE = "https://chateaushatto.com"
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
    venue_id = "chateau_shatto"
    events_url = f"{BASE}/exhibitions"
    source_label = "chateaushatto.com"
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

        # Each exhibition is an <a class="exhibition"> with structured children
        for a_el in soup.find_all("a", class_="exhibition", href=True):
            href = a_el["href"]
            # Skip undefined links
            if "undefined" in href:
                continue
            url = href if href.startswith("http") else BASE + href

            h3 = a_el.find("h3")
            title = h3.get_text(strip=True) if h3 else ""
            if not title or title in seen:
                continue
            seen.add(title)

            h2 = a_el.find("h2")
            artists_text = h2.get_text(strip=True) if h2 else ""
            # Multiple artists may be concatenated; split on capitals
            artists = [s.strip() for s in re.split(r"(?<=[a-z])(?=[A-Z])", artists_text) if s.strip()][:5]

            small = a_el.find("small")
            date_str = small.get_text(strip=True) if small else ""
            start, end = _parse_range(date_str) if date_str else (None, None)

            img = a_el.find("img")
            image = img.get("src") if img else None

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
                image=image,
                artists=artists,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
