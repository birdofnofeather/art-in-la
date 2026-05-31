"""The Broad — Drupal JSON:API.

The public site (/events) is client-rendered, but Drupal exposes a clean
JSON:API at /jsonapi. Events live in `node--nextgen_event` (with a structured
`field_program_date`) and exhibitions in `node--nextgen_exhibition` (with
`field_on_view_dates`). No browser required.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://www.thebroad.org"
API = BASE + "/jsonapi/node"
_TAG_RE = re.compile(r"<[^>]+>")

# Evergreen admission products that aren't real programmed exhibitions.
_SKIP_TITLES = {"general admission"}


def _txt(html_field) -> str:
    if isinstance(html_field, dict):
        html_field = html_field.get("value", "")
    if not html_field:
        return ""
    return _TAG_RE.sub(" ", str(html_field)).replace("&nbsp;", " ").strip()


def _url(attrs: dict) -> str:
    path = attrs.get("path") or {}
    alias = path.get("alias") if isinstance(path, dict) else None
    return BASE + alias if alias else BASE + "/events"


def _paged(url: str, max_pages: int = 6) -> Iterable[dict]:
    """Follow JSON:API pagination, capped."""
    seen = 0
    while url and seen < max_pages:
        r = get(url)
        if not r or r.status_code != 200:
            return
        try:
            data = json.loads(r.text)
        except Exception:
            return
        yield from data.get("data", [])
        url = (data.get("links", {}).get("next") or {}).get("href")
        seen += 1


class Scraper(BaseScraper):
    venue_id = "the_broad"
    events_url = f"{BASE}/events"
    source_label = "thebroad.org"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        yield from self._events()
        yield from self._exhibitions()

    def _events(self) -> Iterable[Event]:
        for node in _paged(f"{API}/nextgen_event?page[limit]=50"):
            a = node.get("attributes", {})
            title = (a.get("title") or "").strip()
            if not title:
                continue
            dates = a.get("field_program_date") or []
            if not isinstance(dates, list) or not dates:
                continue
            first = dates[0] or {}
            start = first.get("value")
            end = first.get("end_value")
            if not start:
                continue
            desc = _txt(a.get("field_overview") or a.get("field_about"))
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=False,
                url=_url(a),
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )

    def _exhibitions(self) -> Iterable[Event]:
        for node in _paged(f"{API}/nextgen_exhibition?page[limit]=50"):
            a = node.get("attributes", {})
            title = (a.get("title") or "").strip()
            if not title or title.lower() in _SKIP_TITLES:
                continue
            dates = a.get("field_on_view_dates") or []
            if not isinstance(dates, list) or not dates:
                continue
            first = dates[0] or {}
            start = first.get("value")
            end = first.get("end_value")
            if not start:
                continue
            desc = _txt(a.get("field_overview") or a.get("field_about"))
            yield Event(
                id=event_id(self.venue_id, start, title + "::exh"),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=_url(a),
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
