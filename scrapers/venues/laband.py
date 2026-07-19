"""Laband Art Gallery (Loyola Marymount University).

The gallery's events page (cfa.lmu.edu/labandgallery/events/) is server-
rendered: each event is a heading followed by description, a "Thu. Apr. 23"
date line and a "5–7p.m." time line. LMU's Localist calendar (cal.lmu.edu)
bot-gates with a 403, so we parse the gallery page itself. No year appears on
the page; we assume the nearest future occurrence (or this year).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable

import pytz

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso
from bs4 import BeautifulSoup

LA = pytz.timezone("America/Los_Angeles")

_MONTHS = {m[:3].lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June","July",
     "August","September","October","November","December"], 1)}
# "Thu. Apr. 23" / "Tues. May, 12"
_DATE_RE = re.compile(r"\b(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)\.?,?\s+([A-Za-z]{3,9})\.?,?\s+(\d{1,2})\b")
# "5–7p.m." / "12-1p.m." / "6:30–8 p.m."
_TIME_RE = re.compile(
    r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*[–—-]\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)",
    re.I)


def _to24(h, m, ap):
    ap = (ap or "").lower().replace(".", "")
    if ap.startswith("p") and h != 12: h += 12
    if ap.startswith("a") and h == 12: h = 0
    return h, m


class Scraper(BaseScraper):
    venue_id = "laband"
    events_url = "https://cfa.lmu.edu/labandgallery/events/"
    source_label = "cfa.lmu.edu"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if resp is None or not resp.ok:
            return
        yield from self.custom_parse(resp.text, str(resp.url))

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        now_iso = now_utc_iso()
        today = date.today()

        # Event cards are div.feature blocks: .feature__title (name),
        # .feature__preheading (description), .feature__heading (date / time /
        # location lines), .feature__cta a (detail link on cal.lmu.edu).
        for card in soup.select("div.feature"):
            title_el = card.select_one(".feature__title")
            heading_el = card.select_one(".feature__heading")
            if not title_el or not heading_el:
                continue
            title = title_el.get_text(" ", strip=True)
            block = heading_el.get_text(" ", strip=True)
            desc_el = card.select_one(".feature__preheading")
            desc = desc_el.get_text(" ", strip=True) if desc_el else ""
            link_el = card.select_one(".feature__cta a[href]")
            link = link_el["href"] if link_el else self.events_url

            dm = _DATE_RE.search(block)
            if not title or not dm:
                continue
            mon = _MONTHS.get(dm.group(1)[:3].lower())
            if not mon:
                continue
            day = int(dm.group(2))
            # Year inference: the page shows no year. Assume this year; only
            # roll to next year when the date is ~a year past (e.g. a January
            # listing scraped in December). Recently-past events stay this
            # year and are archived by the pipeline rather than misdated.
            year = today.year
            try:
                d = date(year, mon, day)
                if (today - d).days > 300:
                    d = date(year + 1, mon, day)
            except ValueError:
                continue

            tm = _TIME_RE.search(block)
            if tm:
                sh, sm = _to24(int(tm.group(1)), int(tm.group(2) or 0), tm.group(3) or tm.group(6))
                eh, em = _to24(int(tm.group(4)), int(tm.group(5) or 0), tm.group(6))
                start = LA.localize(datetime(d.year, d.month, d.day, sh, sm)).isoformat()
                end = LA.localize(datetime(d.year, d.month, d.day, eh, em)).isoformat()
                all_day = False
            else:
                start, end, all_day = d.isoformat(), None, True

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:400],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=all_day,
                url=link,
                image=None,
                source=self.source_label,
                scraped_at=now_iso,
            )
