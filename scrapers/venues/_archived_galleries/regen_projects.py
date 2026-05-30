"""Regen Projects — Artlogic / Collage CMS.

Same server-rendered Artlogic structure as David Kordansky.
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://www.regenprojects.com"
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
    venue_id = "regen_projects"
    events_url = f"{BASE}/exhibitions"
    source_label = "regenprojects.com"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        section = soup.find("section", {"id": "exhibitions-container-main"})
        if not section:
            return

        for entry in section.find_all("div", class_="entry"):
            a = entry.find("a", href=True)
            if not a:
                continue

            href = a["href"]
            url = href if href.startswith("http") else BASE + href

            headers_div = entry.find("div", class_="headers")
            if not headers_div:
                continue

            h1 = headers_div.find("h1")
            h2 = headers_div.find("h2")
            h3 = headers_div.find("h3")

            artist = h1.get_text(strip=True) if h1 else ""
            show_title = h2.get_text(strip=True) if h2 else ""
            date_str = h3.get_text(strip=True) if h3 else ""

            title = f"{artist}: {show_title}" if show_title else artist
            if not title:
                continue

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
