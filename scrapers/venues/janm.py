"""Japanese American National Museum (JANM) — custom Drupal HTML."""
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

BASE = "https://www.janm.org"
# URL path pattern: /events/YYYY-MM-DD/slug
_DATE_RE = re.compile(r"/events/(\d{4}-\d{2}-\d{2})/")
LA_OFFSET = "-07:00"


def _parse_date_text(text: str) -> str | None:
    """Parse 'Friday, May 29, 2026' -> ISO string."""
    try:
        dt = dparser.parse(text, fuzzy=True)
        return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}")
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "janm"
    events_url = f"{BASE}/events"
    source_label = "janm.org"

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

        # Events in div.events-block__home-wrapper
        wrappers = soup.select(".events-block__home-wrapper")
        for wrapper in wrappers:
            # Title and URL from link with date-based href
            link_el = wrapper.find("a", href=_DATE_RE)
            if not link_el:
                # fallback: any link with event-style href
                link_el = wrapper.find("a", href=re.compile(r"/events/\d{4}"))
            if not link_el:
                continue

            href = link_el["href"]
            url = href if href.startswith("http") else BASE + href
            title = link_el.get_text(strip=True)
            if not title:
                # title might be in a sibling/child
                title_el = wrapper.find(["h3", "h4", "h2"])
                title = title_el.get_text(strip=True) if title_el else ""
            if not title or title in seen:
                continue
            seen.add(title)

            # Date: extract from URL path first, then from text
            date_m = _DATE_RE.search(href)
            if date_m:
                start = f"{date_m.group(1)}T00:00:00{LA_OFFSET}"
            else:
                date_div = wrapper.select_one(".events-block__home-dates")
                date_text = date_div.get_text(strip=True) if date_div else ""
                start = _parse_date_text(date_text) if date_text else None

            desc_el = wrapper.select_one(".events-block__home-desc, p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            img_el = wrapper.find("img")
            image = None
            if img_el:
                image = img_el.get("src") or img_el.get("data-src")
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
