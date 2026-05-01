"""Pacific Asia Museum (USC) – scrapes current exhibitions from whats-on-view page."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://pacificasiamuseum.usc.edu"

MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_DATE_RE = re.compile(
    r"(" + MON + r"\s+\d{1,2}(?:,\s*\d{4})?)"
    r"\s*[–—-]+\s*"
    r"(" + MON + r"\s+\d{1,2},\s*\d{4})",
    re.I,
)
_SINGLE_DATE_RE = re.compile(MON + r"\s+\d{1,2},?\s*\d{4}", re.I)

# IDs to skip (past / virtual)
_SKIP_IDS = {"past-exhibitions", "virtual-exhibitions"}


def _parse_date_range(text: str):
    m = _DATE_RE.search(text)
    if m:
        start_raw, end_raw = m.group(1), m.group(2)
        if not re.search(r"\d{4}", start_raw):
            year = re.search(r"\d{4}", end_raw).group()
            start_raw = start_raw.rstrip(",") + f", {year}"
        return start_raw, end_raw
    m2 = _SINGLE_DATE_RE.search(text)
    if m2:
        return m2.group(), None
    return None, None


class Scraper(BaseScraper):
    venue_id = "pacific_asia_museum"
    events_url = f"{BASE}/whats-on-view/"
    source_label = "pacificasiamuseum.usc.edu"

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

        date_re_any = re.compile(
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}",
            re.I,
        )

        # Each anchor-link section is one exhibition block on this page.
        # Structure: <div class="wp-block-uagb-container anchor-link ..." id="...">
        #   <div class="wp-block-group">
        #     <h2>Title</h2>
        #     <p>Date range</p>
        #     <p>Description</p>
        for section in soup.find_all("div", class_="anchor-link"):
            sec_id = section.get("id", "")
            if sec_id in _SKIP_IDS:
                continue

            # Find h2/h3 title
            h = section.find(["h2", "h3", "h4"])
            if not h:
                continue
            title = h.get_text(strip=True)
            if not title:
                continue

            # Find date paragraph (short p with month name)
            date_str = None
            for p in section.find_all("p"):
                pt = p.get_text(strip=True)
                if date_re_any.search(pt) and len(pt) < 100:
                    date_str = pt
                    break

            # Find link
            a = section.find("a", href=re.compile(r"/exhibitions/"))
            if not a:
                a = section.find("a", href=True)
            url = a["href"] if a else self.events_url
            if url and not url.startswith("http"):
                url = BASE + url
            # strip fragment
            url = url.split("#")[0] if url else self.events_url

            if url in seen:
                continue
            seen.add(url)

            start_str, end_str = _parse_date_range(date_str) if date_str else (None, None)
            start = to_la_iso(start_str) if start_str else None
            end = to_la_iso(end_str) if end_str else None

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=infer_type(title, default="exhibition"),
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
