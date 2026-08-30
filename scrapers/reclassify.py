#!/usr/bin/env python3
"""Re-apply the rules to every event we have ever scraped. No network needed.

Use this after editing scrapers/rules.yaml. It reads the stored raw harvest,
re-runs classification, and rewrites events.json, archive.json and the calendar
feeds. Takes a couple of seconds.

    python -m scrapers.reclassify              # apply and write
    python -m scrapers.reclassify --dry-run    # show what would change

The --dry-run comparison is the useful one after a rules edit: it tells you
exactly how many events changed type, and which recurring series appeared or
disappeared, before you commit to anything.
"""
from __future__ import annotations

import argparse
import collections
import sys

from . import storage
from .classify import derive
from .utils.rules import reload as reload_rules


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing files.")
    args = parser.parse_args(argv)

    try:
        rules = reload_rules()
    except Exception as e:
        print(f"rules.yaml could not be loaded: {e}", file=sys.stderr)
        return 2
    print(f"Rules version {rules.version}: "
          f"{len(rules.event_types)} event types, "
          f"{len(rules.recurring_drop)} always-drop patterns.")

    raw = storage.load_raw()
    if not raw:
        print("No raw harvest found (public/data/raw_events.json).", file=sys.stderr)
        print("Run `python -m scrapers.run_all` once to create it.", file=sys.stderr)
        return 1
    print(f"Raw harvest: {len(raw)} records.")

    before = {e["id"]: e for e in storage.load_events() if e.get("id")}
    result = derive(raw)
    after = {e["id"]: e for e in result.upcoming if e.get("id")}

    print()
    print(f"  upcoming          {len(result.upcoming)}")
    print(f"  archive           {len(result.archive)}")
    print(f"  hidden: recurring {len(result.dropped_recurring)}")
    print(f"  hidden: hygiene   {len(result.dropped_hygiene)}")

    # ── What actually changed ────────────────────────────────────────────
    added = set(after) - set(before)
    removed = set(before) - set(after)
    retyped = [
        (before[k].get("event_type"), after[k].get("event_type"), after[k].get("title", ""))
        for k in set(before) & set(after)
        if before[k].get("event_type") != after[k].get("event_type")
    ]
    print()
    print(f"Compared with the current events.json: "
          f"+{len(added)} appeared, -{len(removed)} disappeared, "
          f"{len(retyped)} changed type.")
    if retyped:
        counts = collections.Counter((a, b) for a, b, _ in retyped)
        for (a, b), n in counts.most_common(10):
            print(f"    {n:4d}  {a} -> {b}")
    if removed:
        gone = collections.Counter(before[k].get("venue_id") for k in removed)
        print("  disappeared, by venue: " +
              ", ".join(f"{v}×{n}" for v, n in gone.most_common(8)))

    if args.dry_run:
        print("\n[dry-run] Nothing written.")
        return 0

    storage.write_events(result.upcoming)
    storage.write_archive(result.archive)
    storage.write_feeds(result.upcoming)
    print("\nWrote events.json, archive.json and the calendar feeds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
