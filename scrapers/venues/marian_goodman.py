"""Marian Goodman Gallery – Los Angeles exhibitions (artlogic)."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.mariangoodman.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(\d{1,2}\s+" + MON + r"(?:\s+\d{4})?\s*[-–—]\s*\d{1,2}\s+" + MON + r"(?:,?\s*\d{4})?"
    r"|\d{1,2}\s*[-–—]\s*\d{1,2}\s+" + MON + r"(?:,?\s*\d{4})?)",
    re.I,
)
_EXHB_RE = re.compile(r"/exhibitions/\d+")
_LA_RE = re.compile(r"los.angeles", re.I)


class Scraper(BaseScraper):
    venue_id = "marian_goodman"
    events_url = f"{BASE}/exhibitions"
    source_label = "mariangoodman.com"

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
        for a in soup.find_all("a", href=_EXHB_RE):
            href = a["href"]
            if href in seen:
                continue
            link_text = a.get_text(separator=" ", strip=True)
            if not _LA_RE.search(link_text):
                continue
            seen.add(href)
            url = href if href.startswith("http") else BASE + href
            title = re.sub(r"^Los\s*Angeles\s*", "", link_text, flags=re.I).strip()
            if not title:
                continue
            container = a.parent
            dm = None
            for _ in range(6):
                if container is None:
                    break
                dm = _DATE_RE.search(container.get_text(separator=" ", strip=True))
                if dm:
                    break
                container = container.parent
            date_str = dm.group(1) if dm else ""
            start = to_la_iso(date_str) if date_str else None
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title),
                start=start,
                end=start,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
