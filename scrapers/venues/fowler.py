"""Fowler Museum at UCLA — WordPress with Modern Events Calendar (MEC) plugin."""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://fowler.ucla.edu"
LA_OFFSET = "-07:00"


def _parse_mec_date(date_text: str, time_text: str) -> str | None:
    """Parse 'Sun Apr 26, 2026' + '1:00 pm' into ISO string."""
    combined = f"{date_text} {time_text.split('-')[0].strip()}" if time_text else date_text
    try:
        dt = dparser.parse(combined, fuzzy=True)
        return dt.strftime(f"%Y-%m-%dT%H:%M:%S{LA_OFFSET}")
    except Exception:
        try:
            dt = dparser.parse(date_text, fuzzy=True)
            return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}")
        except Exception:
            return None


class Scraper(BaseScraper):
    venue_id = "fowler"
    events_url = f"{BASE}/events/"
    source_label = "fowler.ucla.edu"

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
        # MEC plugin renders article.mec-event-article for each event
        articles = soup.select("article.mec-event-article")
        seen: set[str] = set()
        for art in articles:
            # Title
            title_el = art.select_one("h3.mec-event-title a, h2.mec-event-title a")
            if not title_el:
                title_el = art.select_one(".mec-event-title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or title in seen:
                continue
            seen.add(title)

            # URL
            link_el = art.find("a", href=True)
            href = link_el["href"] if link_el else ""
            url = href if href.startswith("http") else (BASE + href if href else "")

            # Date: itemprop="startDate" text like "Sun Apr 26, 2026"
            start_el = art.find(itemprop="startDate")
            date_text = start_el.get_text(strip=True) if start_el else ""
            # Time: .mec-time-details text like "1:00 pm-6:00 pm"
            time_el = art.select_one(".mec-time-details")
            time_text = time_el.get_text(strip=True) if time_el else ""
            start = _parse_mec_date(date_text, time_text) if date_text else None

            # Description
            desc_el = art.select_one(".mec-event-description")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # Image
            img_el = art.find("img")
            image = img_el.get("src") if img_el else None
            if image and not image.startswith("http"):
                image = BASE + image

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=None,
                all_day=False,
                url=url or None,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
