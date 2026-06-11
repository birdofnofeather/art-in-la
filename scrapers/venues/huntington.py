"""The Huntington — Next.js calendar behind Vercel's Security Checkpoint.

huntington.org/calendar returns HTTP 429 ("Vercel Security Checkpoint") to
plain clients and even to a headless browser on first paint — but the
checkpoint runs a proof-of-work in the page and self-clears after a couple of
seconds, after which the real calendar renders. `scrapers.utils.render` waits
the checkpoint out and hands us the populated HTML.

Calendar cards look like:

    <article class="…calendar-item-card…">
      <div class="…event-type…">Event</div>
      <a class="…title…" href="/event/slug">Title</a>
      … "June 13, 2026" or "March 17, 2026–Dec. 15, 2026" … description …
    </article>

The cards carry a date (or date range) but no time — showtimes live on the
detail pages — so events are emitted as date-only (all-day) listings.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..base import BaseScraper, Event
from ..utils.render import render_pages
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.huntington.org"

# A single date like "June 13, 2026" or abbreviated "Dec. 15, 2026".
_DATE = r"[A-Z][a-z]{2,8}\.?\s+\d{1,2},\s+\d{4}"
_RANGE_RE = re.compile(rf"({_DATE})\s*[–—-]\s*({_DATE})")
_SINGLE_RE = re.compile(rf"({_DATE})")
# Noise that sits between the title and the date in the card text.
_NOISE_RE = re.compile(r"\b(Sold Out|New|Members Only|Free)\b", re.IGNORECASE)


def _to_iso(date_text: str) -> str | None:
    try:
        dt = dateparser.parse(date_text.replace(".", ""), fuzzy=True)
    except (ValueError, OverflowError):
        return None
    return to_la_iso(dt.date().isoformat(), all_day=True) if dt else None


class Scraper(BaseScraper):
    venue_id = "huntington"
    events_url = f"{BASE}/calendar"
    source_label = "huntington.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        html = render_pages([self.events_url]).get(self.events_url)
        if not html:
            print(f"  [{self.venue_id}] render returned no HTML (checkpoint not cleared)")
            return
        yield from self._parse(html)

    def _parse(self, html: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        now_iso = now_utc_iso()
        cards = soup.select('article[class*="calendar-item-card"]')
        seen: set[str] = set()
        for card in cards:
            title_a = card.select_one('a[class*="title"]')
            if not title_a:
                continue
            title = title_a.get_text(strip=True)
            href = title_a.get("href")
            if not title or not href:
                continue
            url = (BASE + href) if href.startswith("/") else href

            type_el = card.select_one('[class*="event-type"]')
            type_label = type_el.get_text(strip=True) if type_el else ""

            # Pull the date(s) out of the card's text. Strip the title first so a
            # date embedded in a title can't be mistaken for the event date.
            text = card.get_text(" ", strip=True)
            text = text.replace(title, " ")
            text = _NOISE_RE.sub(" ", text)

            start = end = None
            m = _RANGE_RE.search(text)
            if m:
                start = _to_iso(m.group(1))
                end = _to_iso(m.group(2))
            else:
                m = _SINGLE_RE.search(text)
                if m:
                    start = _to_iso(m.group(1))
            if not start:
                continue

            img = card.find("img")
            image = img.get("src") if img else None
            if image and image.startswith("/"):
                image = BASE + image

            if type_label.lower() == "exhibition":
                etype = "exhibition"
            else:
                etype = infer_type(title, default="other")

            ev_id = event_id(self.venue_id, start, title)
            if ev_id in seen:
                continue
            seen.add(ev_id)

            yield Event(
                id=ev_id,
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=etype,
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_iso,
            )
