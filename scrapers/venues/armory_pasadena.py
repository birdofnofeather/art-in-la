"""Armory Center for the Arts (Pasadena) — custom HTML with time[datetime] elements."""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://armoryarts.org"
LA_OFFSET = "-07:00"


class Scraper(BaseScraper):
    venue_id = "armory_pasadena"
    events_url = f"{BASE}/events"
    source_label = "armoryarts.org"

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
        # Events are in div.item-block > div.row > div.col-md-8 > div.inner
        items = soup.find_all("div", class_="item-block")
        for item in items:
            inner = item.find("div", class_="inner")
            if not inner:
                continue

            # Date from time[datetime]
            time_el = inner.find("time", datetime=True)
            raw_date = time_el.get("datetime", "") if time_el else ""
            # raw_date is "YYYY-MM-DD"
            start = f"{raw_date}T00:00:00{LA_OFFSET}" if raw_date else None

            # Title
            title_div = inner.find("div", class_="title")
            if not title_div:
                continue
            title_a = title_div.find("a", href=True)
            title = title_a.get_text(strip=True) if title_a else title_div.get_text(strip=True)
            if not title:
                continue
            href = title_a["href"] if title_a else ""
            url = href if href.startswith("http") else (BASE + href if href else "")

            # Description
            desc_el = inner.find("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # Image
            img_el = item.find("img")
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
