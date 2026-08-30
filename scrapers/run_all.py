#!/usr/bin/env python3
"""Scrape every registered venue, store the raw harvest, publish the listing.

The run has two halves, deliberately kept apart:

  HARVEST     talk to websites, collect whatever they offer, store it untouched
              in public/data/raw_events.json.

  CLASSIFY    apply scrapers/rules.yaml to that harvest to produce the published
              events.json + archive.json (see scrapers/classify.py).

Keeping them apart means a change to the curation rules can be re-applied to
everything ever scraped, in seconds, without touching the network:

    python -m scrapers.reclassify

Run locally:
    python -m scrapers.run_all
    python -m scrapers.run_all --only ica_la --dry-run
    python -m scrapers.run_all --skip-scrape       # re-classify the stored harvest

CI (GitHub Actions) runs this on a cron and commits the results.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from . import monitor, storage
from .classify import derive
from .registry import SCRAPERS
from .utils import llm_extract
from .utils.dedupe import dedupe
from .utils import fleet
from .utils.rules import load as load_rules
from .utils.warn import get_warnings, clear as clear_warnings

# A venue that produced events before but has returned 0 for this many
# consecutive runs gets a health alert (its site layout probably changed).
ZERO_STREAK_ALERT = 3

# Raw records older than this are pruned so the harvest can't grow without end.
RAW_RETENTION_DAYS = 730


def _end_of(ev: dict):
    raw = ev.get("end") or ev.get("start")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def prune_raw(records: list[dict], now=None) -> list[dict]:
    """Drop harvest records that finished more than RAW_RETENTION_DAYS ago."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RAW_RETENTION_DAYS)
    out = []
    for ev in records:
        end = _end_of(ev)
        if end is None or end >= cutoff:
            out.append(ev)
    return out


def scrape(only: set[str] | None) -> tuple[list[dict], list[tuple[str, list]], list[str]]:
    """Run the scrapers. Returns (all_events, per_venue_results, venue_ids_run)."""
    known_venues = {v["id"] for v in storage.load_venues()}

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

    def _run_one(inst):
        try:
            return inst.venue_id, inst.run()
        except BaseException as e:  # one venue must never sink the whole run
            print(f"  [{inst.venue_id}] unhandled exception: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return inst.venue_id, []

    workers = max(1, int(os.environ.get("SCRAPE_WORKERS", "8")))
    if workers == 1:
        results = [_run_one(t) for t in targets]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_run_one, targets))

    all_new: list[dict] = []
    for vid, events in results:
        print(f"→ {vid}: {len(events)} events")
        all_new.extend(events)
    return all_new, results, [t.venue_id for t in targets]


def update_health(results: list[tuple[str, list]]) -> tuple[dict, list]:
    """Track per-venue zero-streaks. Returns (health, venues_needing_attention)."""
    health = storage.load_health()
    today = datetime.now(timezone.utc).date().isoformat()
    stale = []
    for vid, events in results:
        h = health.get(vid) or {}
        if events:
            h = {"zero_streak": 0, "last_success": today}
        else:
            h["zero_streak"] = int(h.get("zero_streak", 0)) + 1
            h.setdefault("last_success", None)
            if h["last_success"] and h["zero_streak"] >= ZERO_STREAK_ALERT:
                stale.append((vid, h["zero_streak"], h["last_success"]))
        health[vid] = h
    return health, stale


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Comma-separated venue_ids to run; omit to run all.")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just print a summary.")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Re-classify the stored harvest without touching the network.")
    parser.add_argument("--no-probe", action="store_true",
                        help="Skip re-fetching venue pages to compare against what we parsed.")
    args = parser.parse_args(argv)

    try:
        rules = load_rules()
    except Exception as e:
        print(f"FATAL: scrapers/rules.yaml could not be loaded: {e}", file=sys.stderr)
        return 2
    print(f"Rules v{rules.version}: {len(rules.event_types)} event types, "
          f"{len(rules.recurring_drop)} always-drop patterns.\n")

    only = {s.strip() for s in args.only.split(",") if s.strip()} if args.only else None

    existing_raw = storage.load_raw()
    health, stale_venues = storage.load_health(), []
    scraped_venue_ids: list[str] = []
    results: list[tuple[str, list]] = []

    # ── Harvest ───────────────────────────────────────────────────────────
    if args.skip_scrape:
        print("--skip-scrape: reclassifying the stored harvest only.\n")
        raw = existing_raw
    else:
        all_new, results, scraped_venue_ids = scrape(only)
        health, stale_venues = update_health(results)

        # Merging the fresh harvest into the stored one.
        #
        # A venue that produced this run has its UPCOMING records replaced
        # wholesale — the scrape is the current truth about what is still to
        # come, so a cancelled event should disappear.
        #
        # Its PAST records are kept regardless. A venue's website stops listing
        # an event once it has happened, so a past record can never be
        # re-harvested: dropping it deletes history. Replacing everything
        # wholesale destroyed the archive in testing, taking it from 757 records
        # to 203 in a single run.
        producing = {e["venue_id"] for e in all_new if e.get("venue_id")}
        now = datetime.now(timezone.utc)
        carryover = []
        for ev in existing_raw:
            if ev.get("venue_id") not in producing:
                carryover.append(ev)
                continue
            end = _end_of(ev)
            if end is not None and end < now:
                carryover.append(ev)          # already happened: this is history
        raw = prune_raw(dedupe(carryover + all_new))
        print(f"\nRaw harvest: {len(raw)} records "
              f"({len(all_new)} fresh, {len(carryover)} carried over).")

    if stale_venues:
        print(f"\n🚨 Health alert: {len(stale_venues)} venue(s) silent for {ZERO_STREAK_ALERT}+ runs:")
        for vid, streak, last in stale_venues:
            print(f"  [{vid}] 0 events for {streak} runs (last produced {last})")

    # ── Classify ──────────────────────────────────────────────────────────
    result = derive(raw)

    # Optional LLM rescue for records dropped purely for a missing date.
    # No-op unless ANTHROPIC_API_KEY is set (a repo secret in CI).
    if result.dropped_hygiene and llm_extract.enabled():
        recovered = llm_extract.recover(result.dropped_hygiene)
        if recovered:
            raw = dedupe(raw + recovered)
            result = derive(raw)
            print(f"LLM fallback: recovered {len(recovered)} event(s)")

    if result.dropped_recurring:
        print(f"\nRecurring filter: hid {len(result.dropped_recurring)} standing-programme events")
        counts = Counter(f"[{e['venue_id']}] {e['title']}" for e in result.dropped_recurring)
        for label, n in counts.most_common(10):
            print(f"  {n:3d}x  {label}")
        if len(counts) > 10:
            print(f"  … and {len(counts) - 10} more unique titles")

    if result.dropped_hygiene:
        print(f"\nHygiene gate: dropped {len(result.dropped_hygiene)} record(s)")
        for label, n in Counter(
            f"[{e.get('venue_id')}] {e.get('title')}" for e in result.dropped_hygiene
        ).most_common(10):
            print(f"  {n:3d}x  {label}")

    print()
    print(f"Total upcoming: {len(result.upcoming)}")
    print(f"Archive total:  {len(result.archive)}")

    warnings = get_warnings()
    print()
    if warnings:
        print(f"Scraper warnings ({len(warnings)} events skipped):")
        for w in warnings[:20]:
            print(f"  [{w['venue_id']}] {w['reason']}: {w['title']}")
    else:
        print("No scraper warnings.")

    # ── Fleet safety gate ─────────────────────────────────────────────────
    # Per-venue checks catch one venue breaking. This catches the shared
    # machinery breaking everything at once, which no per-venue check can see.
    # If it refuses, yesterday's data stays on the site: a day of staleness is
    # a far smaller harm than replacing a working calendar with a broken one.
    gate = fleet.check(result.upcoming, storage.load_events(),
                       result.archive, storage.load_archive())
    print()
    print(gate.summary())

    # ── Status report (the three witnesses) ──────────────────────────────
    health = monitor.record_history(health, results if not args.skip_scrape else [])
    status = monitor.assess(
        published=result.upcoming,
        health=health,
        venues=storage.load_venues(),
        expectations=storage.load_expectations(),
        probe=not args.no_probe,
        scraped_ids=scraped_venue_ids or None,
        harvested={vid: evs for vid, evs in results} if results else None,
    )
    status["published"] = gate.ok
    status["fleet_checks"] = {"blocking": gate.blocking, "warnings": gate.warnings}
    print(f"\nStatus: {status['verdict'].upper()} — "
          f"{status['counts']['red']} red, {status['counts']['yellow']} yellow, "
          f"{status['counts']['green']} green "
          f"(of {status['totals']['venues_checked']} venues checked)")
    for row in status["venues"]:
        if row["verdict"] != "green":
            print(f"  {row['verdict'].upper():6s} {row['venue_id']}: {'; '.join(row['reasons'])}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        clear_warnings()
        return 0

    # The harvest, health and status are always written — they are the record
    # of what happened, including when the publish was refused.
    storage.write_raw(raw)
    storage.write_json(storage.HEALTH_FILE, health)
    storage.write_json(storage.STATUS_FILE, status)
    storage.write_json(storage.WARNINGS_FILE, warnings)
    if scraped_venue_ids:
        storage.write_json(storage.SCRAPED_FILE, sorted(scraped_venue_ids))
    clear_warnings()

    if not gate.ok:
        print("\n❌ Publish refused. events.json and archive.json are unchanged; "
              "the site keeps serving the last good data.")
        return 1

    storage.write_events(result.upcoming)
    storage.write_archive(result.archive)
    storage.write_feeds(result.upcoming)
    print(f"\nWrote events.json ({len(result.upcoming)} events), "
          f"archive.json, raw_events.json, status.json and the calendar feeds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
