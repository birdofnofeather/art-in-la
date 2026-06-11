#!/usr/bin/env python3
"""Run every registered scraper, dedupe, archive past events, write JSON.

Run locally:
    python -m scrapers.run_all

CI (GitHub Actions) runs this on a cron and commits the results.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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
HEALTH_FILE        = DATA_DIR / "health.json"

# A venue that produced events before but has returned 0 for this many
# consecutive runs gets a health alert (its site layout probably changed).
ZERO_STREAK_ALERT = 3


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

    # Build the list of scrapers to run this pass.
    targets = []
    for cls in SCRAPERS:
        inst = cls()
        if only and inst.venue_id not in only:
            continue
        if inst.venue_id not in known_venues:
            print(f"  [warn] scraper venue_id={inst.venue_id} not in venues.json — skipping",
                  file=sys.stderr)
            continue
        targets.append(inst)
    scraped_venue_ids: list[str] = [t.venue_id for t in targets]

    def _run_one(inst):
        try:
            return inst.venue_id, inst.run()
        except BaseException as e:  # one venue must never sink the whole run
            print(f"  [{inst.venue_id}] unhandled exception: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return inst.venue_id, []

    # Scraping is network-bound, so run venues concurrently. Output is order-
    # independent (we dedupe + sort afterwards). Override workers with the
    # SCRAPE_WORKERS env var; set it to 1 to force sequential for debugging.
    all_new: list[dict] = []
    workers = max(1, int(os.environ.get("SCRAPE_WORKERS", "8")))
    if workers == 1:
        results = [_run_one(t) for t in targets]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_run_one, targets))
    for vid, events in results:
        print(f"→ {vid}: {len(events)} events")
        all_new.extend(events)

    # ── Health-gate: flag venues that used to produce events but went silent ──
    health = load_json(HEALTH_FILE, {})
    today = datetime.now(timezone.utc).date().isoformat()
    stale_venues = []
    for vid, events in results:
        h = health.get(vid) or {}
        if events:
            h = {"zero_streak": 0, "last_success": today}
        else:
            h["zero_streak"] = int(h.get("zero_streak", 0)) + 1
            h.setdefault("last_success", None)
            if h["last_success"] and h["zero_streak"] >= ZERO_STREAK_ALERT:
                stale_venues.append((vid, h["zero_streak"], h["last_success"]))
        health[vid] = h
    if stale_venues:
        print(f"\n🚨 Health alert: {len(stale_venues)} venue(s) silent for {ZERO_STREAK_ALERT}+ runs:")
        for vid, streak, last in stale_venues:
            print(f"  [{vid}] 0 events for {streak} runs (last produced {last})")

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
    write_json(HEALTH_FILE,   health)
    clear_warnings()

    print(f"\nWrote {EVENTS_FILE.name} ({len(upcoming)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
