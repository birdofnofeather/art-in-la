"""David Zwirner Los Angeles — Next.js/Sanity CMS site.

Exhibitions are embedded in __NEXT_DATA__ as nowOpen + upcoming lists.
Each entry has startDate, endDate, title, slug, and a locations array.
We filter to Los Angeles shows only.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://www.davidzwirner.com"
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)
LA_OFFSET = "-07:00"


class Scraper(BaseScraper):
    venue_id = "zwirner_la"
    events_url = f"{BASE}/exhibitions"
    source_label = "davidzwirner.com"
    drop_exhibitions = False

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

        data = nd.get("props", {}).get("pageProps", {}).get("data", {})
        all_exh = data.get("nowOpen", []) + data.get("upcoming", [])
        if not isinstance(all_exh, list):
            return

        seen: set[str] = set()
        for ex in all_exh:
            if not isinstance(ex, dict):
                continue
            # Location filter
            locations = ex.get("locations") or []
            is_la = any(
                "angeles" in (loc.get("name") or "").lower()
                for loc in locations
                if isinstance(loc, dict)
            )
            if not is_la:
                continue

            title = (ex.get("title") or "").strip()
            subtitle = (ex.get("subtitle") or "").strip()
            if subtitle:
                title = f"{title}: {subtitle}"
            if not title or title in seen:
                continue
            seen.add(title)

            slug_obj = ex.get("slug") or {}
            slug = slug_obj.get("current", "") if isinstance(slug_obj, dict) else str(slug_obj)
            url = BASE + slug if slug.startswith("/") else (BASE + "/" + slug if slug else self.events_url)

            # Dates are already ISO date strings "YYYY-MM-DD"
            raw_start = ex.get("startDate")
            raw_end = ex.get("endDate")
            start = f"{raw_start}T00:00:00{LA_OFFSET}" if raw_start else None
            end = f"{raw_end}T00:00:00{LA_OFFSET}" if raw_end else None

            # Image from cardViewMedia
            image = None
            media = ex.get("cardViewMedia")
            if isinstance(media, dict):
                image = media.get("url")

            artists_raw = ex.get("artists") or []
            artists = []
            if isinstance(artists_raw, list):
                for a in artists_raw:
                    if isinstance(a, dict) and a.get("name"):
                        artists.append(a["name"])
                    elif isinstance(a, str):
                        artists.append(a)

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
                image=image,
                artists=artists,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
