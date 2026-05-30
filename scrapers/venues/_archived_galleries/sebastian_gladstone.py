"""Sebastian Gladstone — Artlogic CMS, link-text inline date, LA only."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.sebastiangladstone.com"
_EXHB_RE = re.compile(r"/exhibitions/\d+")
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"(\d{1,2}\s+" + MON + r"(?:\s+\d{4})?\s*[-–—]\s*\d{1,2}\s+" + MON + r"(?:,?\s*\d{4})?)",
    re.IGNORECASE,
)
_LA_RE = re.compile(r"los.angeles", re.I)
_NOT_LA_RE = re.compile(r"new.york|london|paris|berlin|hong.kong|new.york", re.I)


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
    venue_id = "sebastian_gladstone"
    events_url = f"{BASE}/exhibitions/"
    source_label = "sebastiangladstone.com"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self):
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not _EXHB_RE.search(href):
                continue
            text = a.get_text(" ", strip=True)
            # Only LA exhibitions (slug or text contains LA, not other cities)
            slug_text = href + " " + text
            if not _LA_RE.search(slug_text):
                continue
            if _NOT_LA_RE.search(slug_text):
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            # Title = text before date, strip trailing location tag "Los Angeles"
            title = text[:m.start()].strip().rstrip(":")
            title = re.sub(r"\s*Los\s*Angeles\s*$", "", title, flags=re.I).strip()
            if not title or title in seen or len(title) < 3:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
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
