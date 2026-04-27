"""Skirball Cultural Center — WordPress, h2/h3 title + next-sibling date span."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.skirball.org"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(?:On\s+view\s+(?:through|from|until)|Opens?)\s+(" + MON + r".{0,50}?\d{4})"
    r"|(" + MON + r"\s+\d{1,2}.{0,40}?\d{4})",
    re.IGNORECASE,
)
_SKIP_RE = re.compile(r"^(menu|nav|search|footer|header|subscribe|donate|visit|plan|about|support)$", re.I)


def _parse_date(raw: str):
    try:
        return to_la_iso(du_parser.parse(raw, fuzzy=True))
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "skirball"
    events_url = f"{BASE}/exhibitions"
    source_label = "skirball.org"

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
        for heading in soup.find_all(["h2", "h3", "h4"]):
            title = heading.get_text(strip=True)
            if not title or len(title) < 3 or len(title) > 150:
                continue
            if _SKIP_RE.match(title):
                continue
            # Look for a date in the next few siblings
            start = end = None
            url = self.events_url
            for sib in heading.find_next_siblings()[:4]:
                sib_text = sib.get_text(" ", strip=True)
                m = _DATE_RE.search(sib_text)
                if m:
                    date_raw = m.group(1) or m.group(2)
                    start = _parse_date(date_raw)
                    # Check for end date after "–" or "through"
                    end_m = re.search(r"[-–—through]\s*(" + MON + r".{0,30}?\d{4})", sib_text, re.I)
                    if end_m:
                        end = _parse_date(end_m.group(1))
                    break
                # Grab URL if present
                a = sib.find("a", href=True)
                if a and not url:
                    href = a["href"]
                    url = href if href.startswith("http") else f"{BASE}{href}"
            if not start:
                continue
            if title in seen:
                continue
            seen.add(title)
            # Get link from heading or nearby
            a = heading.find("a", href=True)
            if not a:
                a = heading.find_next("a", href=True)
            if a:
                href = a["href"]
                url = href if href.startswith("http") else f"{BASE}{href}"
            img = heading.find_next("img")
            image = img.get("src") if img else None
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title, ""),
                start=start,
                end=end or start,
                all_day=True,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
