"""Academy Museum of Motion Pictures — Next.js/Contentful site.

Programs are embedded in __NEXT_DATA__ as cfProgramsKeyedByTkId, a dict of
program objects keyed by Ticketure ID. Each has activeStartDate / activeEndDate
(ISO 8601, UTC), a slug, and a rich-text programTitle field.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.academymuseum.org"
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _rich_text_to_str(rt_field: dict | None) -> str:
    """Extract plain text from Contentful Rich Text JSON."""
    if not rt_field:
        return ""
    try:
        content = rt_field.get("json", {}).get("content", [])
        parts = []
        for block in content:
            for node in block.get("content", []):
                v = node.get("value", "")
                if v:
                    parts.append(v)
        return "".join(parts).strip()
    except Exception:
        return ""


class Scraper(BaseScraper):
    venue_id = "academy_museum"
    events_url = f"{BASE}/en/programs"
    source_label = "academymuseum.org"

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
        m = _NEXT_DATA_RE.search(html)
        if not m:
            return
        try:
            nd = json.loads(m.group(1))
        except Exception:
            return

        programs = nd.get("props", {}).get("pageProps", {}).get(
            "cfProgramsKeyedByTkId", {}
        )
        seen: set[str] = set()
        for prog in programs.values():
            if prog.get("hideFromCalendar"):
                continue

            title = _rich_text_to_str(prog.get("programTitle"))
            if not title:
                title = _rich_text_to_str(prog.get("title"))
            if not title or title in seen:
                continue
            seen.add(title)

            slug = prog.get("slug", "")
            url = f"{BASE}/en/programs/{slug}" if slug else self.events_url

            start = to_la_iso(prog.get("activeStartDate"))
            end = to_la_iso(prog.get("activeEndDate"))

            # Image
            image_data = prog.get("image")
            image = None
            if isinstance(image_data, dict):
                image = image_data.get("url")

            desc = ""
            prog_type = prog.get("__typename", "")

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc,
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=False,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
