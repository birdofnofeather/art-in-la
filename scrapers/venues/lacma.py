"""LACMA events scraper.

LACMA's /event page is Drupal Views with `.card-event` cards -- no JSON-LD,
no WP Tribe API. We parse HTML directly and paginate via ?page=N.

Date format on page: "Sat Apr 25 | 10 am PT" (no year).
Year inference: if the parsed date is >14 days in the past, assume next year.
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
MAX_PAGES = 12


def _parse_lacma_date(raw: str) -> str | None:
    """Parse 'Sat Apr 25 | 10 am PT' -> ISO8601 in LA time."""
    if not raw:
        return None
    text = re.sub(r"\bPT\b", "", raw.replace("|", " ")).strip()
    text = re.sub(r"\s+", " ", text).strip()
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
    venue_id = "lacma"
    events_url = "https://www.lacma.org/event"
    source_label = "lacma.org"

    # Disable base strategies -- this site needs custom HTML parsing
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
            cards = soup.select(".card-event")
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
        name_el = card.select_one(".card-event__name a")
        if not name_el:
            return None
        title = name_el.get_text(strip=True)
        if not title:
            return None
        link = name_el.get("href") or ""
        if link and not link.startswith("http"):
            link = "https://www.lacma.org" + link

        date_el = card.select_one(".card-event__date")
        start = _parse_lacma_date(
            date_el.get_text(separator=" ", strip=True) if date_el else ""
        )

        desc_el = card.select_one(".card-event__content")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        type_el = card.select_one(".card-event__type")
        type_hint = type_el.get_text(strip=True) if type_el else ""

        img_el = card.select_one(".card-event__primary_image img")
        image = img_el.get("src") if img_el else None

        loc_el = card.select_one(".card-event__location")
        location = re.sub(r"\s+", " ", loc_el.get_text(separator=" ", strip=True)).strip() if loc_el else None

        return Event(
            id=event_id(self.venue_id, start, title),
            venue_id=self.venue_id,
            title=title,
            description=desc[:800],
            event_type=infer_type(f"{title} {type_hint}", desc),
            start=start,
            end=None,
            all_day=False,
            url=link or None,
            image=image,
    