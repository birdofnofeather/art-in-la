"""GAVLAK Gallery Los Angeles — Artlogic CMS.

Two entry formats on /exhibitions:
  1. div.entry.full  -> div.headers > h1/h2/h3  (featured banner)
  2. div.entry       -> div.titles[data-categories] > div.title + span.subtitle + span.date

Filter to Los Angeles entries only (data-categories contains "Los Angeles").
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso
from ..utils.http import get

BASE = "https://gavlakgallery.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_LA_RE = re.compile(r"los\s*angeles|los angeles", re.I)
_NON_LA_RE = re.compile(r"palm beach|new york|london|paris|miami", re.I)


def _parse_range(text: str):
    text = text.strip().replace("–", "-").replace("—", "-")
    parts = re.split(r"\s+-\s+", text, maxsplit=1)
    year_m = _YEAR_RE.search(text)
    year = int(year_m.group(1)) if year_m else datetime.now().year
    default = datetime(year, 1, 1)
    try:
        s = parts[0].strip()
        if not _YEAR_RE.search(s):
            s = f"{s} {year}"
        start = dparser.parse(s, default=default, fuzzy=True)
        s_iso = start.strftime("%Y-%m-%dT00:00:00-07:00")
        if len(parts) == 2:
            e = parts[1].strip()
            if not _YEAR_RE.search(e):
                e = f"{e} {year}"
            end_dt = dparser.parse(e, default=start, fuzzy=True)
            e_iso = end_dt.strftime("%Y-%m-%dT00:00:00-07:00")
        else:
            e_iso = None
        return s_iso, e_iso
    except Exception:
        return None, None


def _is_la(location: str) -> bool:
    """Return True if location string refers to Los Angeles."""
    if not location:
        return True  # no location info => assume LA (only location)
    if _LA_RE.search(location):
        return True
    if _NON_LA_RE.search(location):
        return False
    return True  # unknown location, include


class Scraper(BaseScraper):
    venue_id = "gavlak"
    events_url = f"{BASE}/exhibitions"
    source_label = "gavlakgallery.com"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        soup = BeautifulSoup(resp.text, "lxml")
        now = now_utc_iso()
        seen: set[str] = set()

        for entry in soup.find_all("div", class_="entry"):
            a_tag = entry.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag["href"]
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue
            seen.add(url)

            title = date_str = location = ""
            img_tag = entry.find("img")
            image = img_tag.get("src") if img_tag else None

            # Format 1: div.headers with h1/h2/h3 (featured entry)
            headers = entry.find("div", class_="headers")
            if headers:
                h1 = headers.find("h1")
                h2 = headers.find("h2")
                h3 = headers.find("h3")
                title = h1.get_text(strip=True) if h1 else ""
                location = h2.get_text(strip=True) if h2 else ""
                date_str = h3.get_text(strip=True) if h3 else ""
            else:
                # Format 2: div.titles with data-categories
                titles_div = entry.find("div", class_="titles")
                if titles_div:
                    location = titles_div.get("data-categories", "")
                    t = titles_div.find("div", class_="title")
                    d = titles_div.find("span", class_="date")
                    title = t.get_text(strip=True) if t else ""
                    date_str = d.get_text(strip=True) if d else ""

            if not title:
                continue
            if not _is_la(location):
                continue

            start, end = _parse_range(date_str) if date_str else (None, None)

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
                scraped_at=now,
            )
