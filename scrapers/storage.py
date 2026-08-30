"""One place that knows where the data files live and how to read/write them.

Both the scraper (`run_all`) and the re-classifier (`reclassify`) go through
here, so they can never disagree about a path or a JSON format.

The important addition is `raw_events.json` — the untouched harvest, kept so
that classification can be re-run at any time without re-scraping.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"

EVENTS_FILE = DATA_DIR / "events.json"
RAW_FILE = DATA_DIR / "raw_events.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"
VENUES_FILE = DATA_DIR / "venues.json"
WARNINGS_FILE = DATA_DIR / "warnings.json"
SCRAPED_FILE = DATA_DIR / "scraped_venues.json"
HEALTH_FILE = DATA_DIR / "health.json"
STATUS_FILE = DATA_DIR / "status.json"
EXPECTATIONS_FILE = ROOT / "scrapers" / "expectations.json"
FEEDS_DIR = DATA_DIR / "feeds"


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") or default
    except json.JSONDecodeError:
        return default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# ── Convenience readers ───────────────────────────────────────────────────

def load_raw() -> list[dict]:
    return load_json(RAW_FILE, [])


def load_events() -> list[dict]:
    return load_json(EVENTS_FILE, [])


def load_archive() -> list[dict]:
    return load_json(ARCHIVE_FILE, [])


def load_venues() -> list[dict]:
    return load_json(VENUES_FILE, [])


def venues_by_id() -> dict[str, dict]:
    return {v["id"]: v for v in load_venues() if v.get("id")}


def load_health() -> dict:
    return load_json(HEALTH_FILE, {})


def load_expectations() -> dict:
    return load_json(EXPECTATIONS_FILE, {})


# ── Writers ───────────────────────────────────────────────────────────────

def write_raw(records: list[dict]) -> None:
    write_json(RAW_FILE, records)


def write_events(records: list[dict]) -> None:
    write_json(EVENTS_FILE, records)


def write_archive(records: list[dict]) -> None:
    write_json(ARCHIVE_FILE, records)


def write_feeds(upcoming: list[dict]) -> None:
    """Rewrite the subscribable .ics calendar feeds."""
    from .utils.feeds import build_ics

    venues = venues_by_id()
    oneoff = [e for e in upcoming if e.get("event_type") != "exhibition"]
    feeds = {
        "all": (oneoff, "Art in LA — All events"),
        "free": ([e for e in oneoff if e.get("is_free")], "Art in LA — Free events"),
        "family": ([e for e in oneoff if "family" in (e.get("audience") or [])],
                   "Art in LA — Family-friendly"),
    }
    FEEDS_DIR.mkdir(parents=True, exist_ok=True)
    for key, (events, name) in feeds.items():
        (FEEDS_DIR / f"{key}.ics").write_text(
            build_ics(events, venues, name), encoding="utf-8"
        )
