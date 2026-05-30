"""François Ghebaly Gallery — server-side HTML, exhibitions parsed from links."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://ghebaly.com"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–—]\s*"
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",
    re.IGNORECASE,
)


def _parse_range(raw: str):
    raw = re.sub(r"[–—]", " - ", raw)
    parts = [p.strip() for p in re.split(r"\s+-\s+", raw, maxsplit=1)]
    start = end = None
    try:
        start = to_la_iso(du_parser.parse(parts[0], fuzzy=True))
    except Exception:
        pass
    if len(parts) > 1:
        try:
            end = to_la_iso(du_parser.parse(parts[1], fuzzy=True))
        except Exception:
            end = start
    return start, end or start


class Scraper(BaseScraper):
    venue_id = "francois_ghebaly"
    events_url = f"{BASE}/exhibitions/"
    source_label = "ghebaly.com"
    drop_exhibitions: bool = False

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
        container = soup.select_one(".exhibition-list-outer-container") or soup.body
        seen: set[str] = set()
        for a in container.find_all("a", href=True):
            text = a.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if len(lines) < 2:
                continue
            date_line = None
            title_lines = []
            for line in lines:
                if _DATE_RE.search(line):
                    date_line = line
                elif date_line is None:
                    title_lines.append(line)
            if not date_line or not title_lines:
                continue
            title = " ".join(title_lines[:2])
            if title in seen:
                continue
            text_lower = text.lower()
            if "new york" in text_lower or "broadway" in text_lower:
                continue
            seen.add(title)
            date_match = _DATE_RE.search(date_line)
            start, end = _parse_range(date_match.group(1)) if date_match else (None, None)
            href = a.get("href", "")
            url = href if href.startswith("http") else f"{BASE}{href}"
            yield Event(
                id=event_id(self.venue_id, start, title + "::exh"),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end or start,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
