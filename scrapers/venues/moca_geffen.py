"""MOCA Geffen Contemporary — same site as moca.org, filter for Geffen location."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.moca.org"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4}\s*[-–—]\s*" + MON + r"\s+\d{1,2},?\s*\d{4}"
    r"|" + MON + r"\s+\d{1,2}\s*[-–—]\s*" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)


def _pr(raw):
    raw = re.sub(r"[–—]", " - ", raw)
    parts = [p.strip() for p in re.split(r"\s+-\s+", raw, maxsplit=1)]
    s = e = None
    try:
        s = to_la_iso(du_parser.parse(parts[0], fuzzy=True))
    except Exception:
        pass
    if len(parts) > 1:
        try:
            e = to_la_iso(du_parser.parse(parts[1], fuzzy=True))
        except Exception:
            e = s
    return s, e or s


class Scraper(BaseScraper):
    venue_id = "moca_geffen"
    events_url = f"{BASE}/exhibitions"
    source_label = "moca.org"

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
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/exhibition/" not in href:
                continue
            text = a.get_text(" ", strip=True)
            # Only Geffen Contemporary exhibitions
            if "geffen" not in text.lower():
                continue
            # Strip "The Geffen Contemporary at MOCA" prefix
            title = re.sub(r"^The\s+Geffen\s+Contemporary\s+at\s+MOCA\s*", "", text, flags=re.I).strip()
            m = _DATE_RE.search(title)
            if m:
                # Date embedded — extract title as text before or after date
                before = title[:m.start()].strip().rstrip(":")
                after = title[m.end():].strip().lstrip(":")
                title = before if len(before) > len(after) else after
            title = title.strip()
            if not title or title in seen or len(title) < 3:
                continue
            seen.add(title)
            # Try to get date from text
            m2 = _DATE_RE.search(text)
            start, end = _pr(m2.group(0)) if m2 else (None, None)
            url = href if href.startswith("http") else f"{BASE}{href}"
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
