"""MOAH (Lancaster Museum of Art & History).

lancastermoah.org is a Wix site with no structured event data, but MOAH runs
ticketing through an Eventbrite "collection" page. That page embeds a
schema.org ItemList of Event objects inside a plain <script> (not ld+json),
so we extract the itemListElement array with a bracket matcher and map each
item through the standard JSON-LD event builder (offers → free/paid included).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get

COLLECTION = "https://www.eventbrite.com/cc/moah-4338203"


def _extract_array(text: str, key: str):
    """Return the JSON array following '"key":' using a bracket counter."""
    i = text.find(f'"{key}":')
    if i < 0:
        return None
    j = text.find("[", i)
    if j < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for k in range(j, len(text)):
        c = text[k]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
            continue
        if c == '"': in_str = True
        elif c == "[": depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[j:k + 1])
                except json.JSONDecodeError:
                    return None
    return None


class Scraper(BaseScraper):
    venue_id = "moah"
    events_url = "https://www.lancastermoah.org/events"
    source_label = "eventbrite.com/cc/moah"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(COLLECTION)
        if resp is None or not resp.ok:
            return
        items = _extract_array(resp.text, "itemListElement") or []
        seen = set()
        for li in items:
            obj = (li or {}).get("item") if isinstance(li, dict) else None
            if not isinstance(obj, dict) or obj.get("@type") != "Event":
                continue
            key = (obj.get("name"), obj.get("startDate"))
            if key in seen:
                continue
            seen.add(key)
            # The collection page also lists past events and giant recurring
            # date ranges ("Apr 2025 – Jan 2027") — keep only real upcoming
            # listings so raw counts match what a visitor sees on Eventbrite.
            def _d(v):
                try:
                    return datetime.fromisoformat(str(v)[:10]).date()
                except (ValueError, TypeError):
                    return None
            sd, ed = _d(obj.get("startDate")), _d(obj.get("endDate"))
            today = date.today()
            if sd and (ed or sd) < today:
                continue
            if sd and ed and (ed - sd) > timedelta(days=4):
                continue
            yield self._event_from_jsonld(obj)
