"""Diane Rosenstein Gallery — Artlogic CMS, server-rendered link-text."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://dianerosenstein.com"
_EXHB_RE = re.compile(r"/exhibitions/\d+")
_DATE_RE = re.compile(
    r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"(?:\s+\d{4})?\s*[-–—]\s*"
    r"(?:\d{1,2}\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?"
    r"\s*\d{1,2},?\s*\d{4}"
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2}(?:,\s*\d{4})?\s*[-–—]\s*"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?"
    r"\s*\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)

def _parse_range(raw):
    import re as re2
    raw = re2.sub(r"[–—]", " - ", raw)
    parts = [p.strip() for p in re2.split(r"\s+-\s+", raw, maxsplit=1)]
    start = end = None
    try: start = to_la_iso(du_parser.parse(parts[0], fuzzy=True))
    except: pass
    if len(parts) > 1:
        try: end = to_la_iso(du_parser.parse(parts[1], fuzzy=True))
        except: end = start
    return start, end or start

class Scraper(BaseScraper):
    venue_id = "diane_rosenstein"
    events_url = f"{BASE}/exhibitions/"
    source_label = "dianerosenstein.com"
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    def _strategy_custom(self):
        resp = get(self.events_url)
        if not resp or not resp.ok: return
        yield from self.custom_parse(resp.text, resp.url)
    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not _EXHB_RE.search(href): continue
            parent = a.find_parent(["li","div","article"])
            text = parent.get_text(" ", strip=True) if parent else a.get_text(strip=True)
            m = _DATE_RE.search(text)
            if not m: continue
            title = text[:m.start()].strip().rstrip(":")
            if not title or title in seen or len(title) < 3: continue
            seen.add(title)
            start, end = _parse_range(m.group(0))
            url = href if href.startswith("http") else f"{BASE}{href}"
            yield Event(id=event_id(self.venue_id, start, title), venue_id=self.venue_id,
                title=title, description="", event_type="exhibition", start=start, end=end,
                all_day=True, url=url, image=None, source=self.source_label, scraped_at=now_utc_iso())
