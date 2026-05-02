"""
Scraper warning collector.

Usage in any scraper:
    from scrapers.utils.warn import skip_warn

    skip_warn(venue_id, title, "no explicit time in source")

run_all.py calls get_warnings() after all scrapers complete and writes the
result to public/data/warnings.json so it can be reviewed and alerted on.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_warnings: list[dict] = []


def skip_warn(venue_id: str, title: str, reason: str) -> None:
    """Record a skipped event and print a console line so CI logs capture it."""
    entry = {
        "venue_id": venue_id,
        "title": title,
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with _lock:
        _warnings.append(entry)
    print(f"  [{venue_id}] SKIP ({reason}): {title!r}")


def get_warnings() -> list[dict]:
    with _lock:
        return list(_warnings)


def clear() -> None:
    with _lock:
        _warnings.clear()
