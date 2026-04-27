"""MOCA scraper.

MOCA (Museum of Contemporary Art) does not publish a standalone events
calendar.  Their website exposes exhibitions at /exhibitions, each as a
`.column-article` card.

Date ranges appear as "Feb 2026 - Mar 2026" or "Jan 24, 2026-Jan 25, 2027".
We parse these and emit exhibition-type records.

Both MOCA Grand Avenue (moca_grand) and the Geffen Contemporary (moca_geffen)
share the same exhibitions page, so we emit under `moca_grand`.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as du_parser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE_URL = "https://www.moca.org"


def _parse_moca_range(raw: str):
    """Parse 'Feb 2026 - Mar 2026' or 'Jan 24, 2026-Jun 14, 2026' -> (start, end) ISO strings."""
    if not raw:
        return None, None
    cleaned = re.sub(r"[–—]", "-", raw).strip()
    parts = re.split(r"\s*-\s*", cleaned, maxsplit=1)
    start_str = parts[0].strip() if parts else ""
    end_str = parts[1].strip() if len(parts) > 1 else ""
    try:
        start = to_la_iso(du_parser.parse(start_str, default=None)) if start_str else None
    except Exception:
        start = None
    try:
        end = to_la_iso(du_parser.parse(end_str, default=None)) if end_str else None
    except Exception:
        end = None
    return start, end


class Scraper(BaseScraper):
    venue_id = "moca_grand"
    events_url = "https://www.moca.org/exhibitions"
    source_label = "moca.org"

    # Disable base strategies
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    # Keep drop_exhibitions off -- we WANT exhibitions here
    drop_exhibitions: bool = False

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article.column-article")
        if not cards:
            cards = soup.select("article")

        seen: set[str] = set()
        for card in cards:
            link_el = card.find("a", href=True)
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = BASE_URL + href

            title_el = card.find(["h1", "h2", "h3", "h4"])
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            label_el = card.select_one(".label, [class*='date'], [class*='range']")
            date_raw = label_el.get_text(strip=True) if label_el else ""
            start, end = _parse_moca_range(date_raw)

            img_el = card.find("img")
            image = img_el.get("src") or img_el.get("data-src") if img_el else None
            if image and not image.startswith("http"):
                image = BASE_URL + image

            ev = Event(
                id=event_id(self.venue_id, start, title + "::exh"),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=href or None,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),