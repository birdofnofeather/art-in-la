"""JOAN Los Angeles — h2 titles with dates in parent divs."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://joanlosangeles.org"

# Matches "February 21 – May 2, 2026" (with thin-space or regular space around dash)
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,\s*\d{4})?"
    r"[\s ]*[–—―-][\s ]*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+)?\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(20\d\d)\b")

# Skip non-exhibition headings
_SKIP_RE = re.compile(
    r"^(Chapter\s+\w+|Featured|Subscribe|Let'?s\s+stay).*$",
    re.IGNORECASE,
)

# Only include parents that look like exhibition containers (not events/walkthroughs)
_EVENT_PREFIX_RE = re.compile(r"^event\s+", re.IGNORECASE)


def _pr(raw):
    """Parse a date range string, propagating year from end to start if missing."""
    raw = re.sub(r"[–—― ]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    # Find the year
    years = _YEAR_RE.findall(raw)
    year = years[-1] if years else None

    # Split on " - " or just the space where a dash was
    # Re-insert the dash
    raw = re.sub(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,\s*20\d\d)?)\s+"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*20\d\d)",
        r"\1 - \2",
        raw,
        flags=re.IGNORECASE,
    )
    parts = [p.strip() for p in re.split(r"\s+-\s+", raw, maxsplit=1)]
    if len(parts) == 1:
        parts = re.split(r"\s{2,}", raw, maxsplit=1)

    s = e = None
    # Append year to first part if missing
    start_str = parts[0]
    if year and not _YEAR_RE.search(start_str):
        start_str = f"{start_str} {year}"
    try:
        s = to_la_iso(du_parser.parse(start_str, fuzzy=True))
    except Exception:
        pass
    if len(parts) > 1:
        try:
            e = to_la_iso(du_parser.parse(parts[1], fuzzy=True))
        except Exception:
            e = s
    return s, e or s


class Scraper(BaseScraper):
    venue_id = "joan"
    events_url = BASE + "/"
    source_label = "joanlosangeles.org"

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
            if not title or len(title) < 3 or _SKIP_RE.match(title):
                continue
            parent = h.parent
            if not parent:
                continue
            parent_text = parent.get_text(" ", strip=True)
            # Normalize thin spaces
            parent_text = parent_text.replace(" ", " ")
            # Skip event/walkthrough containers
            if _EVENT_PREFIX_RE.match(parent_text):
                continue
            m = _DATE_RE.search(parent_text)
            if not m:
                continue
            if title in seen:
                continue
            seen.add(title)
            date_raw = m.group(0).replace(" ", " ")
            start, end = _pr(date_raw)
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
