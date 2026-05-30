"""Over The Influence — WordPress Avada theme, LA location page."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://overtheinfluence.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
# Date format: "December 2, 2023 / February 18, 2024"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2},?\s*\d{4}\s*/\s*" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.IGNORECASE,
)


def _pr(raw):
    parts = [p.strip() for p in raw.split("/", 1)]
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
    venue_id = "over_the_influence"
    events_url = f"{BASE}/los-angeles/"
    source_label = "overtheinfluence.com"

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
        # Avada theme: article.fusion-post-grid with category-los-angeles
        for article in soup.select("article"):
            classes = " ".join(article.get("class", []))
            if "los-angeles" not in classes and "oti-la" not in classes:
                continue
            # Title from h2
            h2 = article.find("h2")
            if not h2:
                continue
            title = h2.get_text(strip=True)
            if not title or title in seen or len(title) < 3:
                continue
            # Date from any p in the article
            m = None
            for p in article.find_all("p"):
                ptext = p.get_text(" ", strip=True)
                m = _DATE_RE.search(ptext)
                if m:
                    break
            if not m:
                # Try full article text
                text = article.get_text(" ", strip=True)
                m = _DATE_RE.search(text)
            if not m:
                continue
            seen.add(title)
            start, end = _pr(m.group(0))
            a = article.find("a", href=True)
            href = a["href"] if a else ""
            url = href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
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
