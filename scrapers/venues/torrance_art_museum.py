"""Torrance Art Museum — custom CMS, h1 date + h3 titles on exhibitions page."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.torranceartmuseum.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(?:On\s+view\s+(?:from|through|until)?\s*)?(" + MON + r"\s+\d{1,2}.{0,10}?" + MON + r"\s+\d{1,2},?\s*\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}.{0,10}?\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_GALLERY_PREFIX = re.compile(r"^(?:MAIN\s+GALLERY|GALLERY\s+(?:TWO|THREE|ONE|\w+)|DARK\s+ROOM|HALLWAY|TAM\s+HALLWAY)\s*:\s*", re.I)
_SKIP = re.compile(r"^(currently on view|upcoming|semi permanent|public art|permanent|location|mission|hours)$", re.I)


def _pr(raw):
    raw = re.sub(r"[-–—]", " - ", raw)
    parts = [p.strip() for p in re.split(r"\s+-\s+", raw, maxsplit=1)]
    s = e = None
    try:
        s = to_la_iso(du_parser.parse(parts[0], fuzzy=True))
    except Exception:
        pass
    if len(parts) > 1:
        try:
            e = to_la_iso(du_parser.parse(parts[1], fuzzy=True))
        except Exception:
            e = s
    return s, e or s


class Scraper(BaseScraper):
    venue_id = "torrance_art_museum"
    events_url = f"{BASE}/exhibitions"
    source_label = "torranceartmuseum.com"

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
        seen: set[str] = set()
        # Find date block (h1 "On view from DATE")
        current_start = current_end = None
        for el in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = el.get_text(" ", strip=True)
            if not text or len(text) > 200:
                continue
            m = _DATE_RE.search(text)
            if m and el.name in ("h1", "h2"):
                current_start, current_end = _pr(m.group(1))
                continue
            if el.name in ("h3", "h4") and current_start:
                title = _GALLERY_PREFIX.sub("", text).strip()
                if not title or len(title) < 3 or _SKIP.match(title):
                    continue
                # Strip trailing comma or colon
                title = title.strip(",:").strip()
                if title in seen:
                    continue
                seen.add(title)
                a = el.find("a", href=True)
                href = a["href"] if a else ""
                url = href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
                yield Event(
                    id=event_id(self.venue_id, current_start, title),
                    venue_id=self.venue_id,
                    title=title,
                    description="",
                    event_type="exhibition",
                    start=current_start,
                    end=current_end,
                    all_day=True,
                    url=url,
                    image=None,
                    source=self.source_label,
                    scraped_at=now_utc_iso(),
                )
