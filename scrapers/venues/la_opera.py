"""LA Opera — rendered season page (laopera.org/whats-on).

Markup (Nov 2026 snapshot): one card per production —
  div[data-datatype=TessituraItem][data-itemtype=Production]
    a[href^=/performances/] > img[alt]
    div.text-sm.font-medium            "Nov 21 - Dec 13, 2026" | "Nov 15, 2026"
    div.uppercase (title)              "Candide"
Each card is a production run (start–end), published as one record.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Event
from ..utils.dateparse import now_utc_iso
from ..utils.event_id import event_id
from ..utils.generic_listing import parse_dates
from ._rendered import RenderedScraper


class Scraper(RenderedScraper):
    venue_id = "la_opera"
    events_url = "https://www.laopera.org/whats-on"
    source_label = "laopera.org"
    default_event_type = "performance"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        from datetime import date
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for card in soup.select('[data-datatype="TessituraItem"]'):
            a = card.select_one('a[href*="/performances/"]')
            title_el = card.select_one("div.uppercase")
            date_el = next((d for d in card.select("div.text-sm") if re.search(r"\d{4}", d.get_text())), None)
            if not a or not title_el or not date_el:
                continue
            title = title_el.get_text(" ", strip=True)
            got = parse_dates(date_el.get_text(" ", strip=True), date.today())
            if not got or title in seen:
                continue
            seen.add(title)
            start, end, _ = got
            img = card.select_one("img[src]")
            src = img["src"] if img else None
            if src and src.startswith("//"):
                src = "https:" + src
            yield Event(
                id=event_id(self.venue_id, start.isoformat(), title), venue_id=self.venue_id,
                title=title.title() if title.isupper() else title, description="",
                event_type="performance", start=start.isoformat(),
                end=end.isoformat() if end else None, all_day=True,
                url=urljoin("https://www.laopera.org", a["href"]), image=src,
                source=self.source_label, scraped_at=now_utc_iso(),
            )
