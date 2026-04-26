"""Autry Museum of the American West — Drupal HTML calendar."""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://theautry.org"
LA_OFFSET = "-07:00"

# Autry shows recurring/text dates like "Saturdays and Sundays…" which are
# not machine-parseable — we skip those and only emit events with a real date
# embedded in the URL path (/events/category/slug) or a parseable text date.
_DATE_IN_URL = re.compile(r"/events/\w+-activities/|/events/[a-z]")


def _parse_autry_date(text: str) -> str | None:
    """Try to parse a date string like 'June 6, 2026' from Autry event text."""
    # Find something that looks like "Month D, YYYY" or "Month YYYY"
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?", text)
    if not m:
        return None
    try:
        dt = dparser.parse(m.group(0), fuzzy=True)
        return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}")
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "autry"
    events_url = f"{BASE}/events/calendar"
    source_label = "theautry.org"

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
        # Events are article.node-type--event on /events/calendar
        articles = soup.select("article.node-type--event")
        seen: set[str] = set()
        for art in articles:
            link_el = art.find("a", href=True)
            if not link_el:
                continue
            href = link_el["href"]
            url = href if href.startswith("http") else BASE + href

            title_el = art.select_one("h3.event-title, h2.event-title, h3, h2")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or title in seen:
                continue
            seen.add(title)

            # Try to extract a parseable date from the title text
            # (Autry embeds the month/date directly in some event titles)
            date_div = art.select_one(".autry-field-date")
            date_text = date_div.get_text(strip=True) if date_div else ""
            start = _parse_autry_date(date_text) or _parse_autry_date(title)

            # If no parseable date, skip — better to have fewer clean events
            if not start:
                continue

            desc_el = art.select_one(".field--name-body, .event-description, p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            img_el = art.find("img")
            image = img_el.get("src") if img_el else None
            if image and not image.startswith("http"):
                image = BASE + image

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=None,
                all_day=False,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
