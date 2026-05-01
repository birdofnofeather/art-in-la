"""Museum of Tolerance – HubSpot CMS events page."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://museumoftolerance.com"

MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"((?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\w*,\s+" + MON + r"\s+\d{1,2},\s+\d{4})",
    re.I,
)


class Scraper(BaseScraper):
    venue_id = "museum_of_tolerance"
    events_url = f"{BASE}/events"
    source_label = "museumoftolerance.com"

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

        # HubSpot CMS: each event card is a div.hs_cos_wrapper_type_inline_rich_text
        # Text format: "Title | Weekday, Month D, YYYY • H:MM AM/PM"
        for div in soup.find_all("div", class_="hs_cos_wrapper_type_inline_rich_text"):
            txt = div.get_text(separator=" | ", strip=True)
            m = _DATE_RE.search(txt)
            if not m:
                continue

            date_str = m.group(1)
            # Title is text before the date
            title = txt[:m.start()].strip(" |•").strip()
            if not title:
                continue

            # URL from the link in this div
            a = div.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            # strip tracking params
            url = url.split("?")[0]

            if url in seen:
                continue
            seen.add(url)

            start = to_la_iso(date_str) if date_str else None
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title),
                start=start,
                end=start,
                all_day=False,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
