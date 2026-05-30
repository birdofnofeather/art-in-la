"""Philip Martin Gallery — Artlogic CMS, link-text inline date."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://philipmartingallery.com"
_EXHB_RE = re.compile(r"/exhibitions/\d+")
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
# Matches: "2 May - 13 Jun 2026" | "16 - 19 Apr 2026" | "15 Nov 2025 - 17 Jan 2026"
_DATE_RE = re.compile(
    r"(\d{1,2}\s+" + MON + r"(?:\s+\d{4})?\s*[-–—]\s*\d{1,2}\s+" + MON + r"(?:,?\s*\d{4})?"
    r"|\d{1,2}\s*[-–—]\s*\d{1,2}\s+" + MON + r"(?:,?\s*\d{4})?)",
    re.IGNORECASE,
)
# Only keep gallery exhibitions (skip fairs, Berlin, etc.)
_SKIP_RE = re.compile(r"art\s*fair|art\s*basel|frieze|dallas|miami|new\s*york|berlin|paris|london|hong\s*kong", re.I)


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
    venue_id = "philip_martin"
    events_url = f"{BASE}/exhibitions/"
    source_label = "philipmartingallery.com"

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
            if _SKIP_RE.search(text):
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            title = text[:m.start()].strip().rstrip(":")
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
