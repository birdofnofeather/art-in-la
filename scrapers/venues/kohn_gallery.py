"""Michael Kohn Gallery — h2/h3 elements with inline 'Title Date' text."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.kohngallery.com"

# Matches "October 11, 2025 - January 31, 2026" or "August 16 – October 1, 2025"
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,\s*\d{4})?"
    r"\s*[–—―-]\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+)?\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)

# Suffixes to strip
_SUFFIX_RE = re.compile(
    r"\s*(Gallery\s+\d[\d\s,&]*|Opening\s+Reception.*|Curated\s+by.*)$",
    re.IGNORECASE,
)

# Skip section labels
_SKIP_RE = re.compile(
    r"^(Upcoming\s+Exhibition|Current\s+Exhibition|Past\s+Exhibition|Gallery\s+\d)$",
    re.IGNORECASE,
)


def _pr(raw):
    raw = re.sub(r"[–—―]", " - ", raw)
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
    venue_id = "kohn_gallery"
    events_url = f"{BASE}/exhibitions-2"
    source_label = "kohngallery.com"

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

        for h in soup.find_all(["h2", "h3"]):
            text = h.get_text(" ", strip=True)
            if not text or _SKIP_RE.match(text) or len(text) < 3:
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            title = text[:m.start()].strip().rstrip(",").rstrip(":")
            title = _SUFFIX_RE.sub("", title).strip()
            if not title or title in seen or len(title) < 3:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=self.events_url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
