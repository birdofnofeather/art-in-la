"""Avenue 50 Studio — WordPress (The Events Calendar).

The Tribe REST API is disabled on this site (returns 0) and the list page only
carries breadcrumb JSON-LD — but each /event/<slug> detail page emits a clean
schema.org Event. We harvest the event links from the list page and parse each
detail page's Event JSON-LD directly.
"""
from __future__ import annotations

import html
import json
import re
from typing import Iterable

from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://avenue50studio.org"


def _find_event_ld(html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        payload = script.string or script.text
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph", data) if isinstance(data, dict) else data
        for node in (nodes if isinstance(nodes, list) else [nodes]):
            if isinstance(node, dict) and str(node.get("@type", "")).lower() == "event":
                return node
    return None


class Scraper(BaseScraper):
    venue_id = "avenue_50"
    events_url = f"{BASE}/events"
    source_label = "avenue50studio.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        soup = BeautifulSoup(resp.text, "lxml")
        now = now_utc_iso()
        seen: set[str] = set()
        for a in soup.find_all("a", href=re.compile(r"/event/[^/]+/?$")):
            href = a["href"]
            url = (href if href.startswith("http") else BASE + href).rstrip("/")
            if url in seen:
                continue
            seen.add(url)

            detail = get(url)
            if not detail or not detail.ok:
                continue
            ld = _find_event_ld(detail.text)
            if not ld:
                continue
            title = html.unescape((ld.get("name") or "").strip())
            start = to_la_iso(ld.get("startDate"))
            if not title or not start:
                continue
            end = to_la_iso(ld.get("endDate"))
            desc = html.unescape((ld.get("description") or "").strip())
            image = ld.get("image")
            if isinstance(image, dict):
                image = image.get("url")
            elif isinstance(image, list) and image:
                image = image[0]

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day="T" not in (start or ""),
                url=ld.get("url") or url,
                image=image,
                source=self.source_label,
                scraped_at=now,
            )
