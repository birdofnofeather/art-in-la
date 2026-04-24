"""Stable event ID generator for dedup across sources."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Optional


def normalize_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # drop trivial prefixes that vary between sources
    for prefix in ("opening reception for ", "opening reception: ", "opening: ",
                   "closing reception for ", "closing reception: ",
                   "artist talk: ", "lecture: ", "exhibition: "):
        if t.startswith(prefix):
            t = t[len(prefix):]
    return t


def event_id(venue_id: str, start: Optional[str], title: str) -> str:
    """Produce a deterministic id from venue + normalized title + date."""
    date_part = ""
    if start:
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            date_part = dt.date().isoformat()
        except Exception:
            date_part = str(start)[:10]
    norm = normalize_title(title or "")
    raw = f"{venue_id}|{date_part}|{norm}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9-]", "-", norm)[:40].strip("-")
    return f"{venue_id}-{date_part}-{slug}-{digest}" if slug else f"{venue_id}-{date_part}-{digest}"
