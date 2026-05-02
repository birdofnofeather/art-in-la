"""Merge events coming from different sources for the same venue.

Primary key: `id` (produced by event_id.event_id). When two sources produce the
same id we keep the richer record (more non-empty fields) and prefer the one
with an `image`.
"""
from __future__ import annotations

from typing import Iterable


def _score(ev: dict) -> int:
    score = 0
    for k in ("title", "description", "start", "end", "url", "image"):
        v = ev.get(k)
        if v:
            score += 1
            if k == "description" and isinstance(v, str) and len(v) > 200:
                score += 1
    if ev.get("image"):
        score += 1
    if ev.get("artists"):
        score += 1
    return score


def _start_str(e):
    """Return start as a sortable string, handling datetime objects defensively."""
    start = e.get("start") or ""
    if hasattr(start, "isoformat"):
        return start.isoformat()
    return str(start)


def dedupe(events: Iterable[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for ev in events:
        eid = ev.get("id")
        if not eid:
            continue
        incumbent = best.get(eid)
        if incumbent is None or _score(ev) > _score(incumbent):
            best[eid] = ev
    # stable order: by start then title
    return sorted(best.values(), key=lambda e: (_start_str(e), e.get("title") or ""))
