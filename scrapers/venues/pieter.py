"""Pieter Performance Space – Squarespace eventlist."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://pieterpasd.com"
_DATE_RE = re.compile(
    r"((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+\d{4})",
    re.I,
)
_SKIP_RE = re.compile(r"renter.orientation|open.studio", re.I)


class Scraper(BaseScraper):
    venue_id = "pieter"
    events_url = f"{BASE}/programs"
    source_label = "pieterpasd.com"

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
        seen: set[str] = set()
        for item in soup.find_all(class_="eventlist-event"):
            # Prefer the named link (not the image link)
            a = None
            for cand in item.find_all("a", href=re.compile(r"/programs/")):
                t = cand.get_text(strip=True)
                if t and not t.startswith("View"):
                    a = cand
                    break
            if not a:
                continue
            href = a["href"]
            if href in seen:
                continue
            seen.add(href)
            title = a.get_text(strip=True)
            if not title or _SKIP_RE.search(title):
                continue
            url = href if href.startswith("http") else BASE + href
            txt = item.get_text(separator=" ", strip=True)
            m = _DATE_RE.search(txt)
            date_str = m.group(1) if m else ""
            start = to_la_iso(date_str) if date_str else None
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title),
                start=start,
                end=start,
                all_day=False,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
