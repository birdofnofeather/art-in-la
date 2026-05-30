"""Roberts Projects Los Angeles — Artlogic CMS, div.entry variant."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://www.robertsprojectsla.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year


def _parse_range(s: str):
    s = s.strip().replace("–", "-").replace("—", "-").replace("‒", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default)
            return dt.strftime("%Y-%m-%dT00:00:00-07:00"), None
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default)
        end_dt = dparser.parse(end_s, default=default)
        return (
            start_dt.strftime("%Y-%m-%dT00:00:00-07:00"),
            end_dt.strftime("%Y-%m-%dT00:00:00-07:00"),
        )
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "roberts_projects"
    events_url = f"{BASE}/exhibitions"
    source_label = "robertsprojectsla.com"
    drop_exhibitions = False

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        # Roberts uses div.entry without the outer section wrapper
        entries = soup.find_all("div", class_="entry")
        seen: set[str] = set()
        for entry in entries:
            a = entry.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href

            h1 = entry.find("h1")
            h2 = entry.find("h2")
            h3 = entry.find("h3")

            show_title = h1.get_text(strip=True) if h1 else ""
            artist = h2.get_text(strip=True) if h2 else ""
            date_str = h3.get_text(strip=True) if h3 else ""

            title = show_title or artist
            if not title or title in seen:
                continue
            seen.add(title)
            if artist and show_title:
                title = f"{show_title}: {artist}"

            start, end = _parse_range(date_str) if date_str else (None, None)

            img_tag = entry.find("img")
            image = img_tag.get("src") or img_tag.get("data-src") if img_tag else None

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
                artists=[artist] if artist else [],
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
