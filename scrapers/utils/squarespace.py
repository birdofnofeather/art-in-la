"""Squarespace event collections — a proper JSON feed hiding in plain sight.

Any Squarespace page returns its underlying data as JSON if you append
`?format=json`. When the page is an *Events* collection (rather than an
ordinary page), that JSON contains a clean, complete list of events under
`upcoming` and `past`, with real start/end timestamps, links, images and a
full address with coordinates.

This matters because 16 of our venues run on Squarespace and were being read by
hand-written HTML parsers — the most fragile thing in the codebase. Five of
them expose this feed, and the feed is strictly better than what the parsers
were extracting:

    pieter             47 upcoming   (the HTML parser found 24)
    molaa              15 upcoming   (the HTML parser found  9)
    bergamot_station    9 upcoming   (had no scraper at all)
    mak_center          3 upcoming
    las_fotos_project   1 upcoming

The other eleven use a plain `page` collection with hand-placed content and
have no feed — nothing to be done about those here.

Dates arrive as milliseconds since the epoch, in UTC. They are passed through
to_la_iso like every other date in this project, so a real time becomes the
equivalent LA wall-clock and a midnight value collapses to a bare date rather
than a fabricated "12:00 AM".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .http import get


def json_url(events_url: str) -> str:
    """The ?format=json address for a Squarespace page."""
    base = (events_url or "").split("?")[0].rstrip("/")
    return f"{base}?format=json"


def fetch(events_url: str) -> Optional[dict]:
    """Return the parsed collection JSON, or None if this isn't one."""
    resp = get(json_url(events_url))
    if resp is None or not resp.ok:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None          # an HTML error page, not a collection
    if not isinstance(data, dict):
        return None
    # An Events collection always has these two keys, even when both are empty.
    if "upcoming" not in data and "past" not in data:
        return None
    return data


def is_event_collection(data: dict) -> bool:
    """True if this page is a real Events collection with something in it."""
    return bool(data) and bool(data.get("upcoming") or data.get("past"))


def epoch_ms_to_iso(value) -> Optional[str]:
    """Milliseconds since the epoch (UTC) -> an ISO string in UTC.

    Left for to_la_iso to convert; we do not do timezone maths here, so there
    is exactly one place in the project that decides what LA-local means.
    """
    if value in (None, ""):
        return None
    try:
        seconds = int(value) / 1000
    except (TypeError, ValueError):
        return None
    # Guard against a nonsense timestamp becoming a nonsense event.
    if not (0 < seconds < 4_102_444_800):        # up to the year 2100
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def absolute_url(site_url: str, full_url: Optional[str]) -> Optional[str]:
    """Squarespace gives `fullUrl` as a site-relative path."""
    if not full_url:
        return None
    if full_url.startswith(("http://", "https://")):
        return full_url
    from urllib.parse import urlparse
    parsed = urlparse(site_url or "")
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{full_url}"


def location_name(item: dict) -> Optional[str]:
    """A readable location, when the venue set one on the event itself."""
    loc = item.get("location")
    if not isinstance(loc, dict):
        return None
    parts = [loc.get("addressTitle"), loc.get("addressLine1")]
    return ", ".join(p for p in parts if p) or None


def items(data: dict, include_past: bool = False) -> list[dict]:
    """Every event in the collection, upcoming first."""
    out = list(data.get("upcoming") or [])
    if include_past:
        out += list(data.get("past") or [])
    return [i for i in out if isinstance(i, dict)]
