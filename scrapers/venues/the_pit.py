"""The Pit (Glendale) — Squarespace site, SSL cert on www subdomain.

Fetches current and upcoming exhibitions from www.the-pit.la with
verify=False to work around the cert mismatch. Content is partially
server-side rendered in .sqs-html-content blocks as structured text:

  CURRENT EXHIBITIONS
  <Title>
  <Title>

  UPCOMING EXHIBITIONS
  <Date range>:
  <Title>

Date ranges are parsed with dateutil. Current shows get today as start
and a placeholder end 60 days out (no dates in server HTML for current).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests as _requests
from bs4 import BeautifulSoup
from dateutil import parser as du_parser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.the-pit.la"
_VERIFY = False      # SSL cert issued for www.the-pit.la but served on the-pit.la

# Common date range patterns like "May 8-17th, 2026" or "May 16th, 2026"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+[\d\w,\s–\-]+\d{4})",
    re.IGNORECASE,
)

_NAV_WORDS = {
    "HOME", "ARTISTS", "FAIRS", "Exhibitions", "Current Exhibitions",
    "Past Exhibitions", "Upcoming Exhibitions", "EVENTS", "Past Events",
    "Upcoming Events", "PRESS", "SHOP", "ABOUT", "Menu",
    "CURRENT EXHIBITIONS", "UPCOMING EXHIBITIONS", "UPCOMING EVENTS",
}


def _fetch(path: str) -> BeautifulSoup | None:
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            resp = _requests.get(
                f"{BASE}{path}", verify=_VERIFY, timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
    except Exception:
        pass
    return None


def _parse_date_range(raw: str):
    """Try to parse 'May 8-17th, 2026' -> (start_iso, end_iso)."""
    raw = re.sub(r"[–—]", "-", raw).strip()
    # Split on the dash only if it looks like a range
    parts = re.split(r"\s*-\s*(?=\d)", raw, maxsplit=1)
    if len(parts) == 2:
        start_str, end_str = parts
        # If end_str has no month, inherit from start
        if not re.search(r"[A-Za-z]", end_str):
            month_match = re.match(r"([A-Za-z]+)\s+", start_str)
            if month_match:
                end_str = f"{month_match.group(1)} {end_str}"
    else:
        start_str = end_str = raw
    try:
        start_dt = du_parser.parse(start_str.replace("th","").replace("st","").replace("nd","").replace("rd",""), fuzzy=True)
        start = to_la_iso(start_dt)
    except Exception:
        start = None
    try:
        end_dt = du_parser.parse(end_str.replace("th","").replace("st","").replace("nd","").replace("rd",""), fuzzy=True)
        end = to_la_iso(end_dt)
    except Exception:
        end = start
    return start, end


class Scraper(BaseScraper):
    venue_id = "the_pit"
    events_url = ""          # fetched manually below; no base strategy
    source_label = "the-pit.la"
    drop_exhibitions: bool = False

    # Disable auto-strategies — all require events_url to be set
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        now = datetime.now(tz=timezone.utc)
        today_iso = to_la_iso(now)
        default_end = to_la_iso(now + timedelta(days=60))

        # --- CURRENT EXHIBITIONS (no dates on page, use today / +60d) ---
        soup_cur = _fetch("/current-exhibitions")
        if soup_cur:
            for block in soup_cur.select(".sqs-html-content, .sqs-block-content"):
                txt = block.get_text(strip=True)
                if len(txt) < 10 or txt.startswith("HOME"):
                    continue
                for line in block.get_text(separator="\n").splitlines():
                    line = line.strip()
                    if not line or line in _NAV_WORDS or line.upper() in ("CURRENT EXHIBITIONS",):
                        continue
                    yield Event(
                        id=event_id(self.venue_id, today_iso, line + "::exh"),
                        venue_id=self.venue_id,
                        title=line,
                        description="",
                        event_type="exhibition",
                        start=today_iso,
                        end=default_end,
                        all_day=True,
                        url=f"{BASE}/current-exhibitions",
                        image=None,
                        source=self.source_label,
                        scraped_at=now_utc_iso(),
                    )

        # --- UPCOMING EXHIBITIONS ---
        soup_up = _fetch("/upcoming-exhibitions")
        if soup_up:
            for block in soup_up.select(".sqs-html-content, .sqs-block-content"):
                lines = [l.strip() for l in block.get_text(separator="\n").splitlines()
                         if l.strip() and l.strip() not in _NAV_WORDS]
                if not lines:
                    continue
                # Lines alternate: date_line, title_line, date_line, title_line …
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if line.upper() in ("UPCOMING EXHIBITIONS", "CURRENT EXHIBITIONS"):
                        i += 1
                        continue
                    # Is this a date line?
                    date_match = _DATE_RE.search(line)
                    if date_match and i + 1 < len(lines):
                        date_raw = date_match.group(1)
                        title = lines[i + 1]
                        start, end = _parse_date_range(date_raw)
                        if title and title not in _NAV_WORDS:
                            yield Event(
                                id=event_id(self.venue_id, start, title + "::exh"),
                                venue_id=self.venue_id,
                                title=title,
                                description="",
                                event_type="exhibition",
                                start=start,
                                end=end or start,
                                all_day=True,
                                url=f"{BASE}/upcoming-exhibitions",
                                image=None,
                                source=self.source_label,
                                scraped_at=now_utc_iso(),
                            )
                        i += 2
                    else:
                        i += 1
