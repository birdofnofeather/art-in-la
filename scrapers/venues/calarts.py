"""CalArts – events listing page (calarts.edu/events)."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://calarts.edu"

# "Sat, Apr 4 / 12:00 PM - Sun, Jul 5 / 6:00 PM"
# "Fri, May 1 / 1:00 PM - 4:00 PM"
MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
DOW = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*"
_DATE_RE = re.compile(
    r"(" + DOW + r",\s+" + MON + r"\s+\d{1,2})\s*/\s*([\d:]+\s*[AP]M)"
    r"(?:\s*-\s*"
    r"(?:(" + DOW + r",\s+" + MON + r"\s+\d{1,2})\s*/\s*)?"
    r"([\d:]+\s*[AP]M))?",
    re.I,
)

# Skip REDCAT events (already scraped) and external domains
_SKIP_DOMAINS = ("redcat.org", "symplicity.com")


def _parse_calarts_date(txt: str):
    """Return (start_str, end_str) ISO or (None, None)."""
    m = _DATE_RE.search(txt)
    if not m:
        return None, None
    # Infer year = current year (events are upcoming)
    from datetime import datetime
    year = datetime.now().year
    start_dow_mon = m.group(1)  # e.g. "Sat, Apr 4"
    start_time = m.group(2)     # e.g. "12:00 PM"
    end_dow_mon = m.group(3)    # e.g. "Sun, Jul 5" or None
    end_time = m.group(4)       # e.g. "6:00 PM" or None

    def parse(dow_mon, time_str):
        # "Sat, Apr 4" -> "Apr 4"
        mon_day = re.sub(r"^\w+,\s*", "", dow_mon).strip()
        full = f"{mon_day}, {year} {time_str}"
        try:
            dt = datetime.strptime(full, "%b %d, %Y %I:%M %p")
            return dt.strftime("%B %d, %Y %I:%M %p")
        except ValueError:
            return None

    s = parse(start_dow_mon, start_time) if start_dow_mon else None
    e = parse(end_dow_mon, end_time) if end_dow_mon and end_time else None
    return s, e


class Scraper(BaseScraper):
    venue_id = "calarts"
    events_url = f"{BASE}/events"
    source_label = "calarts.edu"

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
        now = now_utc_iso()
        seen: set[str] = set()

        # Cards are duplicated in the HTML (flex-col-reverse + flex-col pairs)
        # Each card has an <a> link; we dedup by URL
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Skip external/REDCAT
            if any(d in href for d in _SKIP_DOMAINS):
                continue
            # Only calarts.edu event links
            if not href.startswith(("https://calarts.edu/", "/")):
                continue
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue

            # Walk up to find card container with date
            card = a
            for _ in range(8):
                card = card.parent
                if card is None:
                    break
                txt = card.get_text(separator=" ", strip=True)
                if _DATE_RE.search(txt) and len(txt) < 2000:
                    break
            else:
                continue

            if card is None:
                continue

            txt = card.get_text(separator=" ", strip=True)
            if not _DATE_RE.search(txt):
                continue

            # Title: first h-tag or first strong text in card
            title_el = card.find(["h2", "h3", "h4", "h1"])
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                # Take text before the "/" category separator
                title = re.split(r"Exhibition/|Performance/|Lecture/|Networking/", txt)[0].strip()
            if not title or len(title) > 200:
                continue

            start_str, end_str = _parse_calarts_date(txt)
            start = to_la_iso(start_str) if start_str else None
            end = to_la_iso(end_str) if end_str else None

            seen.add(url)
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title),
                start=start,
                end=end,
                all_day=False,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
