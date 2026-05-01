"""SCI-Arc Gallery – exhibitions listing page with clean CSS date spans."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.sciarc.edu"


class Scraper(BaseScraper):
    venue_id = "sciarc"
    events_url = f"{BASE}/events/exhibitions"
    source_label = "sciarc.edu"

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
        now = now_utc_iso()
        today = datetime.now()
        seen: set[str] = set()

        for a in soup.find_all("a", class_=re.compile(r"feed__item"), href=True):
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue

            title_el = a.find(class_="feed__item-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            start_el = a.find(class_="feed__item-start-date")
            end_el = a.find(class_="feed__item-end-date")
            start_str = start_el.get_text(strip=True) if start_el else None
            end_str = end_el.get_text(strip=True) if end_el else None

            # Skip past exhibitions
            if end_str:
                try:
                    end_dt = datetime.strptime(end_str, "%B %d, %Y")
                    if end_dt < today:
                        continue
                except ValueError:
                    pass

            start = to_la_iso(start_str) if start_str else None
            end = to_la_iso(end_str) if end_str else None

            seen.add(url)
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title, default="exhibition"),
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
