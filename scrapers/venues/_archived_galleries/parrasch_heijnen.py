"""Parrasch Heijnen Gallery — Squarespace/custom site.

Exhibitions are listed as Squarespace blog posts. Each h1 is a title,
the date is in a nearby <p> element matching a date range pattern,
and the link is in a sibling <a href="/exhibitions/slug">.
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

BASE = "https://parraschheijnen.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year
LA_OFFSET = "-07:00"
_DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"
)


def _parse_range(s: str):
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


class Scraper(BaseScraper):
    venue_id = "parrasch_heijnen"
    events_url = f"{BASE}/exhibitions"
    source_label = "parraschheijnen.com"
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

        for h1 in soup.find_all("h1"):
            title = h1.get_text(strip=True)
            if not title or title in seen:
                continue

            # Walk up to find container with link and date
            container = h1
            for _ in range(6):
                container = container.parent
                if container is None:
                    break
                # Find exhibition link in container
                links = [
                    a for a in container.find_all("a", href=True)
                    if "/exhibitions/" in a["href"] and a["href"] != "/exhibitions/"
                ]
                if links:
                    break

            if not links:
                continue

            href = links[0]["href"]
            url = href if href.startswith("http") else BASE + href

            # Find date paragraph in same container
            date_str = ""
            for p in container.find_all("p"):
                txt = p.get_text(strip=True)
                if _YEAR_RE.search(txt) and _DATE_RE.search(txt):
                    date_str = txt
                    break

            start, end = _parse_range(date_str) if date_str else (None, None)

            # Image
            img = container.find("img")
            image = img.get("src") if img else None

            seen.add(title)
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
