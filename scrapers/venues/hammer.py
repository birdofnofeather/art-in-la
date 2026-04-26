"""Hammer Museum programs-events scraper.

Hammer uses Drupal 10.  There is no WP Tribe API, no iCal feed, and no
JSON-LD on the listing page.  We parse `.result-item--program` cards from
/programs-events and walk paginated pages.

Date format on the listing page:  "Sat Apr 25  7:00 PM"  (in .result-item__occurrence)
The individual event page carries a <time datetime="2026-04-25T19:00:00Z"> element,
but fetching every individual page is expensive.  We parse the listing date and
infer the year the same way the LACMA scraper does.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

import pytz
from bs4 import BeautifulSoup
from dateutil import parser as du_parser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

LA = pytz.timezone("America/Los_Angeles")
MAX_PAGES = 10
BASE_URL = "https://hammer.ucla.edu"


def _parse_hammer_date(raw: str) -> str | None:
    """Parse 'Sat Apr 25  7:00 PM' -> ISO8601 in LA time.  Year is inferred."""
    if not raw:
        return None
    text = re.sub(r"\s+", " ", raw).strip()
    now_la = datetime.now(LA)
    try:
        dt = du_parser.parse(text, default=now_la.replace(tzinfo=None))
        dt_la = LA.localize(dt.replace(tzinfo=None))
        if (now_la - dt_la).days > 14:
            dt_la = dt_la.replace(year=dt_la.year + 1)
        return dt_la.isoformat()
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "hammer"
    events_url = "https://hammer.ucla.edu/programs-events"
    source_label = "hammer.ucla.edu"

    # Disable base strategies
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
        seen: set[str] = set()

        for page_idx in range(MAX_PAGES):
            if page_idx == 0:
                page_html = html
            else:
                resp = get(f"{self.events_url}?page={page_idx}")
                if not resp or resp.status_code != 200:
                    break
                page_html = resp.text

            soup = BeautifulSoup(page_html, "lxml")
            cards = soup.select(".result-item--program")
            if not cards:
                break

            new_count = 0
            for card in cards:
                ev = self._parse_card(card)
                if ev is None or ev.id in seen:
                    continue
                seen.add(ev.id)
                new_count += 1
                yield ev

            if new_count == 0 and page_idx > 0:
                break

    def _parse_card(self, card) -> Event | None:
        # Link wraps the whole card
        link_el = card if card.name == "a" else card.find_parent("a", class_="result-item")
        if link_el is None:
            link_el = card.find("a", class_=re.compile(r"result-item"))
        href = link_el.get("href") if link_el else None
        if href and not href.startswith("http"):
            href = BASE_URL + href

        # Title
        title_el = card.select_one(".result-item__title h3, .result-item__title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        # Category / type hint
        cat_el = card.select_one(".program__category")
        category = cat_el.get_text(separator=" ", strip=True) if cat_el else ""
        category = re.sub(r"\s+", " ", category).strip()

        # Description
        desc_el = card.select_one(".result-item__excerpt")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        # Date -- listed as "Sat Apr 25\n7:00 PM" in .result-item__occurrence
        occ_el = card.select_one(".result-item__occurrence")
        if occ_el:
            day_part = occ_el.find(string=True, recursive=False)
            time_el = occ_el.select_one(".occurrence__time")
            day_str = day_part.strip() if day_part else ""
            time_str = time_el.get_text(strip=True) if time_el else ""
            date_raw = f"{day_str} {time_str}".strip()
        else:
            date_raw = ""
        start = _parse_hammer_date(date_raw) if date_raw else None

        # Image
        img_el = card.select_one("img")
        image = img_el.get("src") if img_el else None
        if image and not image.startswith("http"):
            image = BASE_URL + image

        return Event(
            id=event_id(self.venue_id, start, title),
            venue_id=self.venue_id,
            title=title,
            description=desc[:800],
            event_type=infer_type(f"{title} {category}", desc),
            start=start,
            end=None,
            all_day=False,
            url=href,
            image=image,
            source=self.source_label,
            scraped_at=now_utc_iso(),
        )
