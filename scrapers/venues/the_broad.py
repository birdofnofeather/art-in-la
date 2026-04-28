"""The Broad scraper.

The Broad runs Drupal 10 at thebroad.org/events.  The events listing
uses Drupal Views with `.views-row` cards.  There is no WP Tribe API,
no iCal, and no JSON-LD on the listing page.

As of 2025/2026 the events page frequently shows no upcoming events
("There are currently no upcoming events").  The scraper handles this
gracefully and returns an empty list in that case.
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
BASE_URL = "https://www.thebroad.org"


def _parse_broad_date(raw: str) -> str | None:
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
    venue_id = "the_broad"
    events_url = "https://www.thebroad.org/events"
    source_label = "thebroad.org"

    # Disable base strategies -- Drupal, not WordPress
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

        cards = (
            soup.select(".views-row article")
            or soup.select(".views-row")
            or soup.select("article.node")
        )

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

            time_el = card.find("time")
            if time_el:
                date_raw = time_el.get("datetime") or time_el.get_text(strip=True)
            else:
                date_el = card.select_one("[class*='date'],[class*='when'],[class*='time']")
                date_raw = date_el.get_text(strip=True) if date_el else ""
            start = _parse_broad_date(date_raw) if date_raw else None

            desc_el = card.select_one("[class*='body'],[class*='desc'],[class*='summary'],p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            img_el = card.find("img")
            image = img_el.get("src") if img_el else None
            if image and not image.startswith("http"):
                image = BASE_URL + image

            ev = Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=None,
                all_day=False,
                url=href or None,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
            if ev.id not in seen:
                seen.add(ev.id)
                yield ev
