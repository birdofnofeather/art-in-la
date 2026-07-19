"""ArtCenter College of Design exhibition galleries (Pasadena).

The exhibitions overview links /about/exhibitions/<slug>.html detail pages
whose text carries "On view March 14 through August 8, 2026" (and often an
"Opening Reception: Saturday, March 14, 2026, 5 to 7 p.m." line, which the
pipeline classifies separately if listed as its own page).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso
from bs4 import BeautifulSoup

BASE = "https://www.artcenter.edu"
_ONVIEW = re.compile(
    r"On view\s+([A-Z][a-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?\s+through\s+([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})")
_MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July",
     "August","September","October","November","December"], 1)}
_SKIP = {"overview", "bloomberg-connects"}
_MAX_PAGES = 24


class Scraper(BaseScraper):
    venue_id = "artcenter"
    events_url = f"{BASE}/about/exhibitions/overview.html"
    source_label = "artcenter.edu"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if resp is None or not resp.ok:
            return
        soup0 = BeautifulSoup(resp.text, "lxml")
        links = []
        for a in soup0.find_all("a", href=True):
            path = a["href"].split("?")[0]
            if not path.startswith("/about/exhibitions/") or not path.endswith(".html"):
                continue
            slug = path.rsplit("/", 1)[-1].removesuffix(".html")
            if slug in _SKIP or path in links:
                continue
            links.append(path)
        now_iso = now_utc_iso()
        for path in links[:_MAX_PAGES]:
            r = get(BASE + path)
            if r is None or not r.ok:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            text = (soup.find("main") or soup).get_text(" ", strip=True)
            m = _ONVIEW.search(text)
            if not m:
                continue
            # Title: the text right before "On view" ends with the show name;
            # prefer the <title> tag's first segment.
            title = (soup.find("title").get_text(strip=True) if soup.find("title") else "").split(" - ")[0].strip()
            if not title:
                continue
            sm = _MONTHS.get(m.group(1)); em = _MONTHS.get(m.group(4))
            if not sm or not em:
                continue
            ey = int(m.group(6))
            sy = int(m.group(3)) if m.group(3) else (ey if sm <= em else ey - 1)
            start = f"{sy:04d}-{sm:02d}-{int(m.group(2)):02d}"
            end = f"{ey:04d}-{em:02d}-{int(m.group(5)):02d}"
            if date.fromisoformat(end) < date.today():
                continue  # archived show still listed on the overview page
            desc = text[m.end():m.end() + 350].strip()
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc,
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=BASE + path,
                image=None,
                source=self.source_label,
                scraped_at=now_iso,
            )
