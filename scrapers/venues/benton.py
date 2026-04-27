"""Benton Museum of Art at Pomona College — link-text with date + title."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.pomona.edu"
_EXHB_RE = re.compile(r"/museum/exhibitions/\d{4}/")
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4}\s*[-–—]\s*" + MON + r"\s+\d{1,2},?\s*\d{4}"
    r"|" + MON + r"\s+\d{1,2}\s*[-–—]\s*" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)
_SKIP_TEXT = re.compile(r"^(all (past|future) exhibitions?|upcoming)$", re.I)


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
    venue_id = "benton"
    events_url = f"{BASE}/museum/exhibitions"
    source_label = "pomona.edu/museum"

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
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not _EXHB_RE.search(href):
                continue
            text = a.get_text(" ", strip=True)
            if _SKIP_TEXT.match(text):
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            # Date may be at start or end of text
            before = text[:m.start()].strip().rstrip(":").strip()
            after = text[m.end():].strip().lstrip(":").strip()
            title = before if len(before) >= len(after) else after
            if not title or title in seen or len(title) < 3:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            url = href if href.startswith("http") else f"{BASE}{href}"
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
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
