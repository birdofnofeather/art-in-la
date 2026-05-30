"""William Turner Gallery — Squarespace, p-element with 'TITLE Date Exhibition Page'."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://williamturnergallery.com"

# Matches "April 25 - June 20, 2026" or "August 6 - October 1, 2022" or "November 15, 2025 - January 10, 2026"
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,\s*\d{4})?"
    r"\s*[-–—]\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+)?\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)

# Off-site exhibition labels to skip
_OFFSITE_RE = re.compile(
    r"(@|Museum|Gallery(?!\s+is)|Laguna|MOLAA|Luckman|ArtCenter|Fair)",
    re.IGNORECASE,
)

# Suffixes to strip from title
_SUFFIX_RE = re.compile(
    r"\s*(Opening Reception:.*|Exhibition Page.*|Event Page.*)$",
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
    venue_id = "william_turner"
    events_url = f"{BASE}/exhibitions/"
    source_label = "williamturnergallery.com"

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

        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            m = _DATE_RE.search(text)
            if not m:
                continue
            # Skip off-site exhibitions
            if _OFFSITE_RE.search(text):
                continue
            # Title is everything before the date
            title = text[:m.start()].strip().rstrip(":")
            title = _SUFFIX_RE.sub("", title).strip()
            if not title or title in seen or len(title) < 2:
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
