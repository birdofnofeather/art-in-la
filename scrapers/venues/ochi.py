"""Ochi Gallery — /exhibition/slug links, filter for Los Angeles."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.ochigallery.com"
_EXHB_RE = re.compile(r"/exhibition/[^/]+/?$")

# Matches "April 11 - May 23, 2026" with optional tabs/spaces
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}"
    r"(?:,\s*\d{4})?\s*[-–—]\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+)?\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)


def _pr(raw):
    raw = re.sub(r"[–—]", " - ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
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
    venue_id = "ochi"
    events_url = f"{BASE}/exhibitions/"
    source_label = "ochigallery.com"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self):
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not _EXHB_RE.search(href):
                continue
            text = a.get_text(" ", strip=True)
            # Normalize whitespace (tabs between date parts)
            text = re.sub(r"[ \t]+", " ", text)

            # Only keep Los Angeles events
            if "los angeles" not in text.lower():
                continue

            m = _DATE_RE.search(text)
            if not m:
                continue

            # Title is before the date
            title = text[:m.start()].strip().rstrip(":")
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
