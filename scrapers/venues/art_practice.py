"""Art + Practice – WP site, exhibitions listing page with dates in card text."""
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

BASE = "https://artandpractice.org"

MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
# "April 18, 2026–September 5, 2026" or "April 18, 2026 – September 5, 2026"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4})"
    r"\s*[–—-]+\s*"
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.I,
)


class Scraper(BaseScraper):
    venue_id = "art_practice"
    events_url = f"{BASE}/exhibitions"
    source_label = "artandpractice.org"

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
        today = datetime.now()

        for a in soup.find_all("a", href=re.compile(r"/exhibitions/exhibition/")):
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue

            # Walk up to find the card container with the full text
            card = a
            for _ in range(6):
                card = card.parent
                if card is None:
                    break
                txt = card.get_text(separator=" ", strip=True)
                if _DATE_RE.search(txt):
                    break

            if card is None:
                continue

            txt = card.get_text(separator=" ", strip=True)
            m = _DATE_RE.search(txt)
            if not m:
                continue

            start_str, end_str = m.group(1), m.group(2)
            start = to_la_iso(start_str)
            end = to_la_iso(end_str)

            # Skip exhibitions that have already ended
            try:
                end_dt = datetime.strptime(end_str.strip(), "%B %d, %Y")
                if end_dt < today:
                    continue
            except ValueError:
                pass

            # Title: the link text or h-tag inside the card
            title_el = card.find(["h1", "h2", "h3", "h4"])
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                title = a.get_text(strip=True) or ""
            if not title:
                continue

            seen.add(url)
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
