"""Craig Krull Gallery — Squarespace, /current-exhibitions page."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.craigkrullgallery.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(" + MON + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–—]\s*" + MON + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}"
    r"|" + MON + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",
    re.IGNORECASE,
)
_SKIP_TEXT = re.compile(r"^(?:exhibitions?|past|current|next|future|join|los angeles|copyright|bergamot)$", re.I)


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
    venue_id = "craig_krull"
    events_url = f"{BASE}/current-exhibitions"
    source_label = "craigkrullgallery.com"

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
        # Only leaf sqs-html-content divs (no nested sqs-html-content children)
        for block in soup.select("div.sqs-html-content"):
            if block.select("div.sqs-html-content"):
                continue  # skip parent blocks
            text = block.get_text(" ", strip=True)
            if not text or len(text) < 10:
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            title = text[:m.start()].strip().rstrip(":").rstrip("|").strip()
            # Strip nav labels from start
            title = re.sub(r"^(?:PAST|CURRENT|NEXT|FUTURE)(?:\s*\|\s*(?:PAST|CURRENT|NEXT|FUTURE))*\s*", "", title, flags=re.I).strip()
            if not title or title in seen or len(title) < 3:
                continue
            if _SKIP_TEXT.match(title):
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            a = block.find("a", href=True)
            href = a["href"] if a else ""
            url = href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
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
