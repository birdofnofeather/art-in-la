"""Brand Library & Art Center — Wix site, find div with 'On view' date."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.brandlibrary.org"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(?:On\s+view\s+(?:through|until|from))\s+(" + MON + r".{0,40}?\d{4})"
    r"|(" + MON + r"\s+\d{1,2}.{0,30}?\d{4})",
    re.IGNORECASE,
)
_SKIP = re.compile(r"^(current\s+exhibition|upcoming|brand\s+library|connect|site\s+map|follow|newsletter|resources)$", re.I)


def _parse_date(raw):
    try:
        return to_la_iso(du_parser.parse(raw, fuzzy=True))
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "brand_library"
    events_url = f"{BASE}/"
    source_label = "brandlibrary.org"

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
        # Find any leaf element containing a date phrase
        for el in soup.find_all(["p", "span", "div"]):
            if el.find(["p", "div", "span"]):
                continue
            text = el.get_text(" ", strip=True)
            m = _DATE_RE.search(text)
            if not m:
                continue
            # Walk up to find the exhibition container
            container = el.find_parent(["div", "section", "article", "li"])
            if not container:
                continue
            container_text = container.get_text(" ", strip=True)
            # Title = container text before the date phrase
            m2 = _DATE_RE.search(container_text)
            if not m2:
                continue
            raw_title = container_text[:m2.start()].strip()
            # Strip "CURRENT EXHIBITION" or similar headers
            raw_title = re.sub(r"^(?:CURRENT|UPCOMING)\s+EXHIBITION\s*", "", raw_title, flags=re.I).strip()
            if not raw_title or raw_title in seen or len(raw_title) < 3:
                continue
            if _SKIP.match(raw_title):
                continue
            seen.add(raw_title)
            date_raw = m2.group(1) or m2.group(2) or ""
            start = _parse_date(date_raw)
            yield Event(
                id=event_id(self.venue_id, start, raw_title),
                venue_id=self.venue_id,
                title=raw_title,
                description="",
                event_type="exhibition",
                start=start,
                end=None,
                all_day=True,
                url=self.events_url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
