"""Los Angeles Municipal Art Gallery (LAMAG) – current exhibitions from homepage + individual pages."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://lamag.org"

MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2}(?:,\s*\d{4})?)"
    r"\s*[-–—]+\s*"
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.I,
)

_SKIP_SLUGS = {
    "archive", "museum-education-and-tours", "free-virtual-classes",
    "lamag-70th-anniversary", "about-us", "contact", "donate", "subscribe",
}


def _parse_date_range(text: str):
    m = _DATE_RE.search(text)
    if not m:
        return None, None
    start_raw, end_raw = m.group(1), m.group(2)
    if not re.search(r"\d{4}", start_raw):
        year = re.search(r"\d{4}", end_raw).group()
        start_raw = start_raw.rstrip(",") + f", {year}"
    return start_raw, end_raw


class Scraper(BaseScraper):
    venue_id = "lamag"
    events_url = f"{BASE}/"
    source_label = "lamag.org"

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
        today = datetime.now()
        seen: set[str] = set()

        # Collect unique internal exhibition URLs from the homepage
        exhibition_urls: list[str] = []
        for a in soup.find_all("a", href=re.compile(r"^https://lamag\.org/")):
            href = a["href"].rstrip("/")
            slug = href.split("/")[-1]
            if slug in _SKIP_SLUGS or not slug:
                continue
            if any(s in slug for s in _SKIP_SLUGS):
                continue
            if href not in seen:
                seen.add(href)
                exhibition_urls.append(href)

        for url in exhibition_urls:
            resp2 = get(url)
            if not resp2 or not resp2.ok:
                continue
            page = BeautifulSoup(resp2.text, "lxml")

            # Title: h1 with class elementor-heading-title — split on <br>
            h1 = page.find("h1")
            if not h1:
                continue
            # Get parts split by <br> tags
            parts = [t.strip() for t in h1.get_text(separator="\n").split("\n") if t.strip()]
            title = parts[0] if parts else ""
            if not title:
                continue

            # Date: from h1 second part, or from page text
            date_text = parts[1] if len(parts) > 1 else ""
            if not _DATE_RE.search(date_text):
                date_text = page.get_text(separator=" ")
            start_str, end_str = _parse_date_range(date_text)

            # Skip exhibitions that ended in the past
            if end_str:
                try:
                    end_dt = datetime.strptime(end_str.strip(), "%B %d, %Y")
                    if end_dt < today:
                        continue
                except ValueError:
                    pass
            # Skip if no dates at all (can't confirm it's current)
            if not start_str:
                continue

            start = to_la_iso(start_str)
            end = to_la_iso(end_str) if end_str else None

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title, default="exhibition"),
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
