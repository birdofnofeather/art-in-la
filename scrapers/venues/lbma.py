"""Long Beach Museum of Art — h2 title + date in parent div."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.lbma.org"

# Matches "February 6, 2026—May 31, 2026" or "March 20, 2026—June 7, 2026"
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s*\d{4}"
    r"\s*[–—―-]\s*"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s*\d{4})",
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
    venue_id = "lbma"
    events_url = f"{BASE}/exhibitions/"
    source_label = "lbma.org"

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

        for h in soup.find_all("h2"):
            title = h.get_text(" ", strip=True)
            if not title or len(title) < 3:
                continue
            parent = h.parent
            if not parent:
                continue
            parent_text = parent.get_text(" ", strip=True)
            m = _DATE_RE.search(parent_text)
            if not m:
                continue
            if title in seen:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            # Try to find a link in the parent or nearby
            a = parent.find("a", href=True) or h.find("a", href=True)
            url = (a.get("href", "") or "") if a else ""
            if url and not url.startswith("http"):
                url = BASE + url
            if not url:
                url = self.events_url
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
