"""Decide whether the code-repair agent should run today, and on which venue.

Tier 1 of self-healing (utils/llm_extract.py, Claude Haiku) fixes the DATA when
a venue's parser breaks: it reads the page and recovers the listings. But it
cannot fix the CODE — and some breakage (a bespoke scraper crashing, a site
moved to a new URL) needs the code changed. That is tier 2: an agent that
rewrites one venue's scraper (.github/workflows/repair-scraper.yml).

Tier 2 costs more per run, so it is rationed here:

* only a venue with its own module in scrapers/venues/ (config-driven venues
  have no code to repair — their reading is already the LLM's job);
* only when the venue has produced nothing for REPAIR_AFTER_ZERO_RUNS runs in
  a row (i.e. tier 1 did not rescue it either);
* never a venue whose site is unreachable (yellow — their problem, not ours;
  "repairing" working code against a site that blocks us does harm);
* at most MAX_REPAIRS_PER_MONTH runs a month, and never the same venue twice
  within REPAIR_COOLDOWN_DAYS.

Prints a JSON decision for the workflow: {"run": bool, "venue": id, "why": ...}
and, with --record, logs the attempt in scrapers/state/repair_ledger.json.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "scrapers" / "state" / "repair_ledger.json"
REPAIR_AFTER_ZERO_RUNS = 4
MAX_REPAIRS_PER_MONTH = 2
REPAIR_COOLDOWN_DAYS = 21


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def decide(today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"run": False, "why": "ANTHROPIC_API_KEY not set"}
    ledger = _load(LEDGER, {"attempts": []})
    month = today.strftime("%Y-%m")
    this_month = [a for a in ledger["attempts"] if a.get("date", "").startswith(month)]
    if len(this_month) >= MAX_REPAIRS_PER_MONTH:
        return {"run": False, "why": f"monthly limit reached ({MAX_REPAIRS_PER_MONTH})"}

    health = _load(ROOT / "public" / "data" / "health.json", {})
    status = _load(ROOT / "public" / "data" / "status.json", {})
    unreachable = set(status.get("unreachable") or [])
    recent = {}
    for a in ledger["attempts"]:
        try:
            recent[a["venue"]] = max(recent.get(a["venue"], date.min), date.fromisoformat(a["date"]))
        except (KeyError, ValueError):
            pass

    modules = _module_paths()
    candidates = []
    for vid, h in health.items():
        if not isinstance(h, dict):
            continue
        if int(h.get("zero_streak") or 0) < REPAIR_AFTER_ZERO_RUNS or not h.get("last_success"):
            continue        # never worked → not a regression; nothing to restore
        if vid in unreachable:
            continue
        module = modules.get(vid)          # venue ids don't always match file names
        if module is None:
            continue
        if vid in recent and (today - recent[vid]).days < REPAIR_COOLDOWN_DAYS:
            continue
        candidates.append((int(h["zero_streak"]), vid))
    if not candidates:
        return {"run": False, "why": "no venue needs a code repair"}
    candidates.sort(reverse=True)
    streak, vid = candidates[0]
    return {"run": True, "venue": vid, "module": modules[vid],
            "why": f"{vid} silent for {streak} runs"}


def _module_paths() -> dict[str, str]:
    """venue_id → repo-relative path of its BESPOKE scraper module."""
    from .registry import SCRAPERS
    out = {}
    for cls in SCRAPERS:
        mod = cls.__module__                       # e.g. scrapers.venues.moca
        if not mod.startswith("scrapers.venues.") or mod.endswith("._generic"):
            continue
        path = mod.replace(".", "/") + ".py"
        if (ROOT / path).exists():
            out[cls.venue_id] = path
    return out


def record(venue: str, outcome: str) -> None:
    ledger = _load(LEDGER, {"attempts": []})
    ledger["attempts"].append({"date": datetime.now(timezone.utc).date().isoformat(),
                               "venue": venue, "outcome": outcome})
    ledger["attempts"] = ledger["attempts"][-50:]
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", nargs=2, metavar=("VENUE", "OUTCOME"))
    a = ap.parse_args()
    if a.record:
        record(*a.record)
    else:
        print(json.dumps(decide()))
