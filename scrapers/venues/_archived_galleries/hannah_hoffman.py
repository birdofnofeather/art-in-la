"""Hannah Hoffman Gallery – Los Angeles exhibitions."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://hannahhoffmangallery.com"
_NY_RE = re.compile(r"new-?york", re.I)
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(r"(" + MON + r"\s+\d{1,2}\s*[-–]\s*" + MON + r"?\s*\d{1,2}\s+\d{4})", re.I)
_NAV = {"/exhibitions/current/", "/exhibitions/past/", "/exhibitions/upcoming/"}


class Scraper(BaseScraper):
    venue_id = "hannah_hoffman"
    events_url = BASE
    source_label = "hannahhoffmangallery.com"

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
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/exhibitions/" not in href or href in _NAV:
                continue
            if _NY_RE.search(href):
                continue
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue
            seen.add(url)

            txt = a.get_text(separator=" | ", strip=True)
            m = _DATE_RE.search(txt)
            date_str = m.group(1) if m else ""
            title = _DATE_RE.sub("", txt).strip(" |").strip()
            if not title:
                continue
            start = to_la_iso(date_str) if date_str else None

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=("opening" if re.search(r"(opening|reception|vernissage|preview)", title, re.I) else "exhibition"),
                start=start,
                end=start,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
