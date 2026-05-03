#!/usr/bin/env python3
"""Run every registered scraper, dedupe, archive past events, write JSON.

Run locally:
    python -m scrapers.run_all

CI (GitHub Actions) runs this on a cron and commits the results.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .registry import SCRAPERS
from .utils.dedupe import dedupe
from .utils.archive import split
from .utils.warn import get_warnings, clear as clear_warnings
from .utils.recurring import filter_recurring


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "public" / "data"
EVENTS_FILE        = DATA_DIR / "events.json"
ARCHIVE_FILE       = DATA_DIR / "archive.json"
VENUES_FILE        = DATA_DIR / "venues.json"
WARNINGS_FILE      = DATA_DIR / "warnings.json"
SCRAPED_FILE       = DATA_DIR / "scraped_venues.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") or default
    except json.JSONDecodeError:
        return default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Comma-separated venue_ids to run; omit to run all.")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just print a summary.")
    args = parser.parse_args(argv)

    existing     = load_json(EVENTS_FILE,  [])
    archive      = load_json(ARCHIVE_FILE, [])
    known_venues = {v["id"] for v in load_json(VENUES_FILE, [])}

    only: set[str] | None = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}

    all_new: list[dict] = []
    scraped_venue_ids: list[str] = []

    for cls in SCRAPERS:
        inst = cls()
        if only and inst.venue_id not in only:
            continue
        if inst.venue_id not in known_venues:
            print(f"  [warn] scraper venue_id={inst.venue_id} not in venues.json — skipping",
                  file=sys.stderr)
            continue
        print(f"→ {inst.venue_id} ({cls.__module__})")
        scraped_venue_ids.append(inst.venue_id)
        try:
            events = inst.run()
        except BaseException as e:
            print(f"  [{inst.venue_id}] unhandled exception: {type(e).__name__}: {e}",
                  file=sys.stderr)
            events = []
        print(f"  {len(events)} events")
        all_new.extend(events)

    # Merge: existing records survive unless the scraper for their venue ran this time.
    producing_venues = {e["venue_id"] for e in all_new}
    carryover = [e for e in existing if e.get("venue_id") not in producing_venues]
    combined  = dedupe(carryover + all_new)

    # ── Filter recurring standing programmes ───────────────────────────────────
    combined, recurring_dropped = filter_recurring(combined)
    if recurring_dropped:
        print(f"\nRecurring filter: dropped {len(recurring_dropped)} standing-programme events")
        from collections import Counter
        counts = Counter(
            f"[{e['venue_id']}] {e['title']}" for e in recurring_dropped
        )
        for label, n in counts.most_common(10):
            print(f"  {n:3d}x  {label}")
        if len(counts) > 10:
            print(f"  … and {len(counts) - 10} more unique titles")

    # Move past events to archive.
    upcoming, past = split(combined)
    archive_combined = dedupe(archive + past)

    print()
    print(f"Total upcoming: {len(upcoming)}  (was {len(existing)})")
    print(f"Archived now:   {len(past)} new past events")
    print(f"Archive total:  {len(archive_combined)}")

    # ── Warnings (missing date/time) ───────────────────────────────────────────
    warnings = get_warnings()
    print()
    if warnings:
        print(f"Scraper warnings ({len(warnings)} events skipped due to missing date/time):")
        for w in warnings:
            print(f"  [{w['venue_id']}] {w['reason']}: {w['title']}")
    else:
        print("No scraper warnings.")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        clear_warnings()
        return 0

    write_json(EVENTS_FILE,   upcoming)
    write_json(ARCHIVE_FILE,  archive_combined)
    write_json(WARNINGS_FILE, warnings)
    write_json(SCRAPED_FILE,  sorted(scraped_venue_ids))
    clear_warnings()

    print(f"\nWrote {EVENTS_FILE.name} ({len(upcoming)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
