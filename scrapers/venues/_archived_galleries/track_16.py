"""Track 16 — p-element pairs (title then date) on /exhibitions/."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://track16.com"

# Matches date ranges like "March 20 - May 9, 2026" or "May 7 - 10, 2026"
_DATE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}"
    r"(?:\s*[-–—]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+)?\d{1,2})?"
    r",?\s*\d{4})",
    re.IGNORECASE,
)

# Section labels / locations to skip (not exhibition titles)
_SKIP_RE = re.compile(
    r"^(CURRENT|UPCOMING|PAST|EXHIBITIONS?|EAST HOLLYWOOD|DOWNTOWN(?: LA)?|"
    r"LOS ANGELES|SANTA MONICA|ArtCenter.*|Opening reception.*|Opening night.*)$",
    re.IGNORECASE,
)

# Art fair / off-site patterns to skip
_FAIR_RE = re.compile(
    r"(Art Fair|Art Book Fair|Museum|Pioneertown|ArtCenter)",
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
    venue_id = "track_16"
    events_url = f"{BASE}/exhibitions/"
    source_label = "track16.com"

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
        ps = soup.find_all("p")
        seen: set[str] = set()

        i = 0
        while i < len(ps) - 1:
            candidate_title = ps[i].get_text(" ", strip=True)
            candidate_date = ps[i + 1].get_text(" ", strip=True)

            if _DATE_RE.match(candidate_date) and candidate_date == candidate_date.strip():
                # Next p is a date — current p should be the title
                title = candidate_title
                date_text = candidate_date

                if (title and not _SKIP_RE.match(title) and not _FAIR_RE.search(title)
                        and title not in seen and len(title) >= 3):
                    m = _DATE_RE.search(date_text)
                    if m:
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
                i += 2
            else:
                i += 1
