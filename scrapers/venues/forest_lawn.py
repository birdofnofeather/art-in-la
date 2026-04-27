"""Forest Lawn Museum — heading + parent-div contains date and description."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://museum.forestlawn.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4}\s*[-–—]\s*" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)
_SKIP = re.compile(r"^(visiting hours?|admission|about|plan your visit|contact|home)$", re.I)


def _pr(raw):
    raw = re.sub(r"[–—]", " - ", raw)
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
    venue_id = "forest_lawn"
    events_url = f"{BASE}/"
    source_label = "museum.forestlawn.com"

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
        for heading in soup.find_all(["h2", "h3", "h4"]):
            title = heading.get_text(strip=True)
            if not title or len(title) < 3 or len(title) > 150 or _SKIP.match(title):
                continue
            parent = heading.find_parent(["div", "section", "article", "li"])
            if not parent:
                continue
            ptext = parent.get_text(" ", strip=True)
            m = _DATE_RE.search(ptext)
            if not m:
                continue
            if title in seen:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            a = parent.find("a", href=True)
            href = a["href"] if a else ""
            url = href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
            img = parent.find("img")
            image = img.get("src") if img else None
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
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
