"""Shoshana Wayne Gallery — Squarespace collectionlink blocks.

Exhibitions page sections (h2 headers): Current / Upcoming / Past.
We scrape Current and Upcoming only.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://www.shoshanawayne.com"
_DATE_RE = re.compile(
    r"(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2}(?:\s*[,–—-]\s*"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?\s*\d{1,2},?\s*\d{4})"
    r"|\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})",
    re.I,
)
_YEAR = datetime.now().year
_DASH = re.compile(r"\s*[–—-]\s*")


def _parse_range(text: str):
    text = text.strip()
    m = _DATE_RE.search(text)
    if not m:
        return None, None
    raw = m.group(0)
    parts = _DASH.split(raw, maxsplit=1)
    default = datetime(_YEAR, 1, 1)
    try:
        s = dparser.parse(parts[0].strip(), default=default, fuzzy=True)
        start = s.strftime(f"%Y-%m-%dT00:00:00-07:00")
        if len(parts) == 2:
            e_text = parts[1].strip()
            if not re.search(r"\d{4}", e_text):
                e_text = f"{e_text} {_YEAR}"
            end = dparser.parse(e_text, default=s, fuzzy=True).strftime(f"%Y-%m-%dT00:00:00-07:00")
        else:
            end = None
        return start, end
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "shoshana_wayne"
    events_url = f"{BASE}/exhibitions"
    source_label = "shoshanawayne.com"

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

        # Find sections between h2 headers: Current and Upcoming only
        raw = html
        h2_positions = [(m.start(), m.group(1).strip())
                        for m in re.finditer(r'<h2[^>]*>([^<]+)</h2>', raw, re.I)]

        # Build slices for Current and Upcoming sections
        sections = []
        for i, (pos, label) in enumerate(h2_positions):
            if label.lower() in ("current", "upcoming"):
                end = h2_positions[i + 1][0] if i + 1 < len(h2_positions) else len(raw)
                sections.append(raw[pos:end])

        seen: set[str] = set()
        for section_html in sections:
            section_soup = BeautifulSoup(section_html, "lxml")
            for item in section_soup.find_all("div", class_="collectionlink-content"):
                title_el = item.find("div", class_="collectionlink-title")
                desc_el = item.find("div", class_="collectionlink-description")
                if not title_el:
                    continue
                link_el = title_el.find("a", href=True)
                title = title_el.get_text(strip=True)
                href = link_el["href"] if link_el else ""
                if not href:
                    continue
                url = href if href.startswith("http") else BASE + href
                if url in seen:
                    continue
                seen.add(url)

                desc_text = desc_el.get_text(separator=" ", strip=True) if desc_el else ""
                start, end = _parse_range(desc_text)

                yield Event(
                    id=event_id(self.venue_id, start, title),
                    venue_id=self.venue_id,
                    title=title,
                    description=desc_text,
                    event_type="exhibition",
                    start=start,
                    end=end,
                    all_day=True,
                    url=url,
                    image=None,
                    source=self.source_label,
                    scraped_at=now,
                )
