"""Sprüth Magers Los Angeles — WordPress custom theme.

Exhibitions are article.exhib-tile elements with class 'los-angeles' for
LA shows. Checks both current (/exhibitions/) and upcoming (/exhibitions/upcoming/).
"""
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

BASE = "https://spruethmagers.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year
LA_OFFSET = "-07:00"


def _parse_range(s: str):
    """Parse 'May 15–August 8, 2026' → (start_iso, end_iso)."""
    s = s.strip().replace("–", "-").replace("—", "-").replace("‒", "-")
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


def _scrape_page(url: str, venue_id: str, source_label: str) -> Iterable[Event]:
    resp = get(url)
    if not resp or not resp.ok:
        return
    soup = BeautifulSoup(resp.text, "lxml")
    for tile in soup.find_all("article", class_="exhib-tile"):
        classes = tile.get("class", [])
        if "los-angeles" not in classes:
            continue

        # Title: alt text of image or text content
        img = tile.find("img")
        title = img.get("alt", "").strip() if img else ""
        if not title:
            h_el = tile.find(["h1", "h2", "h3", "h4"])
            title = h_el.get_text(strip=True) if h_el else ""
        # Clean "– Los Angeles" suffix from alt text
        title = re.sub(r"\s*[–\-]\s*Los Angeles\s*$", "", title).strip()
        if not title:
            continue

        # Date from first pipe-delimited text segment matching a date range
        full_text = tile.get_text(separator="|", strip=True)
        date_str = ""
        for segment in full_text.split("|"):
            if _YEAR_RE.search(segment) and re.search(r"[A-Z][a-z]+\s+\d", segment):
                date_str = segment.strip()
                break

        start, end = _parse_range(date_str) if date_str else (None, None)

        # URL from tile id
        tile_id = tile.get("id", "")
        url_link = f"{BASE}/exhibitions/{tile_id}/" if tile_id else url

        image = img.get("src") if img else None

        # Description
        desc_el = tile.find("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        yield Event(
            id=event_id(venue_id, start, title),
            venue_id=venue_id,
            title=title,
            description=desc[:800],
            event_type="exhibition",
            start=start,
            end=end,
            all_day=True,
            url=url_link,
            image=image,
            source=source_label,
            scraped_at=now_utc_iso(),
        )


class Scraper(BaseScraper):
    venue_id = "sprueth_magers"
    events_url = f"{BASE}/exhibitions/"
    source_label = "spruethmagers.com"
    drop_exhibitions = False

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        seen: set[str] = set()
        for page_url in [self.events_url, f"{BASE}/exhibitions/upcoming/"]:
            for ev in _scrape_page(page_url, self.venue_id, self.source_label):
                if ev.title not in seen:
                    seen.add(ev.title)
                    yield ev
