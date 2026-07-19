"""JACCC (Japanese American Cultural & Community Center, Little Tokyo).

WordPress with a custom events listing (no Tribe REST, no JSON-LD). The
listing page links /events/<slug>/ detail pages whose server-rendered text
carries a "When  Sat, Jul 25, 2026 - Sat, Sep 26, 2026 10:00 am" block.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

import pytz

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso
from bs4 import BeautifulSoup

LA = pytz.timezone("America/Los_Angeles")
_LINK = re.compile(r'href="(https://jaccc\.org/events/[^"/]+/)"')
_WHEN = re.compile(
    r"When\s+\w{3},\s+(\w{3})\s+(\d{1,2}),\s+(\d{4})"          # start date
    r"(?:\s*-\s*\w{3},\s+(\w{3})\s+(\d{1,2}),\s+(\d{4}))?"     # optional end date
    r"(?:\s+(\d{1,2}):(\d{2})\s*(am|pm))?",                    # optional time
    re.I,
)
_MONTHS = {m: i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
_MAX_PAGES = 16


class Scraper(BaseScraper):
    venue_id = "jaccc"
    events_url = "https://jaccc.org/events/"
    source_label = "jaccc.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if resp is None or not resp.ok:
            return
        links = []
        for url in _LINK.findall(resp.text):
            if url not in links:
                links.append(url)
        now_iso = now_utc_iso()
        for url in links[:_MAX_PAGES]:
            r = get(url)
            if r is None or not r.ok:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            title_el = soup.find("h1") or soup.find("title")
            title = (title_el.get_text(" ", strip=True) if title_el else "").split("|")[0].strip()
            text = (soup.find("main") or soup).get_text(" ", strip=True)
            m = _WHEN.search(text)
            if not title or not m:
                continue
            sm, sd, sy = _MONTHS.get(m.group(1)[:3].title()), int(m.group(2)), int(m.group(3))
            if not sm:
                continue
            end = None
            all_day = True
            if m.group(7):  # has a time
                h, mi = int(m.group(7)), int(m.group(8))
                if m.group(9).lower() == "pm" and h != 12: h += 12
                if m.group(9).lower() == "am" and h == 12: h = 0
                start = LA.localize(datetime(sy, sm, sd, h, mi)).isoformat()
                all_day = False
            else:
                start = f"{sy:04d}-{sm:02d}-{sd:02d}"
            if m.group(4):
                em, ed, ey = _MONTHS.get(m.group(4)[:3].title()), int(m.group(5)), int(m.group(6))
                if em:
                    end = f"{ey:04d}-{em:02d}-{ed:02d}"
            # description: text after the When block
            desc = text[m.end():m.end() + 350].strip()
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc,
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=all_day,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now_iso,
            )
