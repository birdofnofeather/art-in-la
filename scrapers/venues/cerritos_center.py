"""Cerritos Center for the Performing Arts — rendered home-page carousel.

The site refuses non-browser HTTP clients outright, so it is rendered.
Markup (Nov 2026 snapshot): slick carousel items (div.item, clones marked
.slick-cloned are skipped) with
  p.secondary-heading  "FRI, NOV 20 / 8:00 PM"   (no year — inferred)
  p.heading            "An Evening of Alton Brown"
  p.link > a[href]     ticket link
"""
from __future__ import annotations

from datetime import date
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Event
from ..utils.dateparse import now_utc_iso, to_la_iso
from ..utils.event_id import event_id
from ..utils.generic_listing import parse_dates
from ._rendered import RenderedScraper


class Scraper(RenderedScraper):
    venue_id = "cerritos_center"
    events_url = "https://www.cerritoscenter.com/"
    source_label = "cerritoscenter.com"
    default_event_type = "performance"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for item in soup.select("div.item"):
            if "slick-cloned" in item.get("class", []):
                continue
            when = item.select_one("p.secondary-heading")
            head = item.select_one("p.heading")
            if not when or not head:
                continue
            got = parse_dates(when.get_text(" ", strip=True), date.today())
            if not got:
                continue
            d, _, tm = got
            title = head.get_text(" ", strip=True)
            start = to_la_iso(f"{d.isoformat()}T{tm}:00") if tm else d.isoformat()
            if (title, start) in seen:
                continue
            seen.add((title, start))
            a = item.select_one("p.link a[href]")
            img = item.select_one("img[src]")
            yield Event(
                id=event_id(self.venue_id, start, title), venue_id=self.venue_id,
                title=title, description="", event_type="performance",
                start=start, end=None, all_day="T" not in start,
                url=a["href"] if a else self.events_url,
                image=urljoin(self.events_url, img["src"]) if img else None,
                source=self.source_label, scraped_at=now_utc_iso(),
            )
