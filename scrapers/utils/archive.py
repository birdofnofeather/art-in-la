"""Move past events to archive.json and prune the main events.json."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

import pytz

LA = pytz.timezone("America/Los_Angeles")


def _end_of_event(ev: dict) -> datetime | None:
    """Best-effort 'when did this event finish?'"""
    raw = ev.get("end") or ev.get("start")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = LA.localize(dt)
    # If all-day or date-only, treat as end-of-day LA
    if len(str(raw)) == 10:
        dt = LA.localize(datetime(dt.year, dt.month, dt.day, 23, 59))
    return dt


def split(events: list[dict]) -> Tuple[list[dict], list[dict]]:
    """Return (upcoming, past) based on end-of-event vs. now LA-time."""
    now = datetime.now(tz=timezone.utc)
    upcoming, past = [], []
    for ev in events:
        end = _end_of_event(ev)
        if end is None:
            # Unknown when it ends — keep it upcoming; safer than losing it.
            upcoming.append(ev)
            continue
        if end < now:
            past.append(ev)
        else:
            upcoming.append(ev)
    return upcoming, past
