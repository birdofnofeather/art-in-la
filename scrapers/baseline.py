#!/usr/bin/env python3
"""Write or refresh scrapers/expectations.json — what "normal" looks like per venue.

This is the third witness. History tells you what a venue HAS been doing, which
is no help when it has been quietly broken for two months; the source page tells
you what it offers today. An expectation is the separate statement of what it
SHOULD be doing, which is the only one of the three that can catch a venue that
has been wrong since the day it was written.

    python -m scrapers.baseline              # fill in anything not yet recorded
    python -m scrapers.baseline --refresh    # recompute every venue from history
    python -m scrapers.baseline --show lacma

The generated bounds are deliberately loose — they exist to catch collapse and
runaway, not to police normal variation. Tighten any of them by hand; hand-set
values are marked `"source": "human"` and are never overwritten.

The exhibitions figure matters most. 26 venues currently publish events and
zero exhibitions, and nothing has ever flagged it, because a venue returning
events looks alive. Setting `min_exhibitions` for a museum that plainly has
shows on is how that becomes visible.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from . import storage

# Bounds are set this far either side of observed normal.
LOWER = 0.4
UPPER = 3.0


def _observed(events: list[dict]) -> dict[str, dict]:
    counts: dict[str, dict] = {}
    for ev in events:
        entry = counts.setdefault(ev["venue_id"], {"events": 0, "exhibitions": 0})
        key = "exhibitions" if ev.get("event_type") == "exhibition" else "events"
        entry[key] += 1
    return counts


def build(existing: dict, published: list[dict], health: dict,
          venues: list[dict], refresh: bool = False) -> dict:
    observed = _observed(published)
    out = dict(existing)
    today = datetime.now(timezone.utc).date().isoformat()

    for venue in venues:
        vid = venue.get("id")
        if not vid:
            continue
        current = out.get(vid) or {}
        if current.get("source") == "human" and not refresh:
            continue          # never overwrite a deliberate decision
        if current and not refresh:
            continue

        seen = observed.get(vid)
        history = [v for v in (health.get(vid) or {}).get("recent_counts") or []
                   if isinstance(v, int)]
        if not seen and not history:
            continue          # nothing to base an expectation on yet

        typical_events = seen["events"] if seen else 0
        typical_exh = seen["exhibitions"] if seen else 0
        if history:
            typical_events = max(typical_events, int(sum(history) / len(history)))

        out[vid] = {
            "min_events": max(0, int(typical_events * LOWER)),
            "max_events": max(5, int(typical_events * UPPER)),
            # Left at 0 by default: asserting a venue *should* have exhibitions
            # is an editorial judgement about that venue, so it is yours to make.
            # Setting it is how a museum with shows on but none scraped becomes
            # visible instead of looking healthy.
            "min_exhibitions": typical_exh if typical_exh else 0,
            "source": "generated",
            "updated": today,
            "note": venue.get("short_name") or venue.get("name") or vid,
        }
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="Recompute every venue, except those marked source=human.")
    parser.add_argument("--show", metavar="VENUE_ID", help="Print one venue's expectation.")
    args = parser.parse_args(argv)

    existing = storage.load_expectations()

    if args.show:
        entry = existing.get(args.show)
        print(json.dumps(entry, indent=2) if entry
              else f"no expectation recorded for {args.show!r}")
        return 0 if entry else 1

    updated = build(
        existing,
        published=storage.load_events(),
        health=storage.load_health(),
        venues=storage.load_venues(),
        refresh=args.refresh,
    )
    added = len(updated) - len(existing)
    storage.write_json(storage.EXPECTATIONS_FILE, dict(sorted(updated.items())))
    print(f"expectations.json: {len(updated)} venues "
          f"({added} added, {len(existing)} already recorded)")
    human = sum(1 for v in updated.values() if v.get("source") == "human")
    if human:
        print(f"  {human} hand-set and left untouched")
    print("\nEdit any entry by hand and set \"source\": \"human\" to freeze it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
