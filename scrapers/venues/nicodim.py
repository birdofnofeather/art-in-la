"""Nicodim Gallery — Artlogic CMS, div.entry with h2 location filter."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://www.nicodimgallery.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year
LA_OFFSET = "-07:00"


def _parse_range(s: str):
    s = s.strip().replace("–", "-").replace("—", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default)
            return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"), None
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default)
        end_dt = dparser.parse(end_s, default=default)
        return (
            start_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
            end_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
        )
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "nicodim"
    events_url = f"{BASE}/exhibitions"
    source_label = "nicodimgallery.com"
    drop_exhibitions = False

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        for entry in soup.find_all("div", class_="entry"):
            # h2 contains the location
            h2 = entry.find("h2")
            loc = h2.get_text(strip=True) if h2 else ""
            if loc and "angeles" not in loc.lower():
                continue

            a = entry.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href

            h1 = entry.find("h1")
            h3 = entry.find("h3")
            title = h1.get_text(strip=True) if h1 else ""
            if not title or title in seen:
                continue
            seen.add(title)

            date_str = h3.get_text(strip=True) if h3 else ""
            start, end = _parse_range(date_str) if date_str else (None, None)

            img = entry.find("img")
            image = img.get("src") or img.get("data-src") if img else None

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
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
