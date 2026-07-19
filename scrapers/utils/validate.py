"""Pre-publish hygiene gate.

Runs on the upcoming-events list right before it is written to events.json, so
undated ghosts and stale records never reach the UI. Every drop is recorded via
skip_warn() so it surfaces in warnings.json.

Rules:
  1. A non-exhibition with no parseable start date -> drop (can't place it).
  2. An exhibition with NO start AND NO end -> drop, unless it was scraped within
     GRACE_DAYS (a newly-listed show whose dates haven't been parsed yet).
  3. Any event whose entire known date range ended more than 1 day ago -> drop
     (it belongs in the archive, not the live list).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from .warn import skip_warn

GRACE_DAYS = 45


def _parse(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate(events, now=None):
    """Return (kept, dropped)."""
    now = now or datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    grace = now - timedelta(days=GRACE_DAYS)
    kept, dropped = [], []

    def _drop(ev, reason):
        dropped.append(ev)
        skip_warn(ev.get("venue_id", "?"), ev.get("title", ""), f"dropped ({reason})")

    for ev in events:
        is_exh = (ev.get("event_type") == "exhibition") or (
            "exhibition" in (ev.get("event_types") or [])
        )
        start = _parse(ev.get("start"))
        end = _parse(ev.get("end"))

        if not is_exh and start is None:
            _drop(ev, "no start date")
            continue

        # A "one-off" event spanning more than a few days is a standing
        # programme (e.g. "Guided Tours  May 28 – Jul 23"), not a listing a
        # person can put on a calendar. The reshape step keeps its real type;
        # we drop it here so it never tops the What's On list.
        if not is_exh and start is not None and end is not None:
            if (end - start) > timedelta(days=4):
                _drop(ev, "multi-week range, not a one-off event")
                continue

        if is_exh and start is None and end is None:
            scraped = _parse(ev.get("scraped_at"))
            if scraped is None or scraped < grace:
                _drop(ev, "undated exhibition past grace window")
                continue
            kept.append(ev)
            continue

        finish = end or start
        if finish is not None and finish < day_ago:
            _drop(ev, "date range already ended")
            continue

        kept.append(ev)
    return kept, dropped
