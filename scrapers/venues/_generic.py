"""Config-driven scrapers for venues with no bespoke parser.

Every venue listed in scrapers/generic_venues.yaml gets a scraper built from
its entry — no Python per venue. Each one runs the standard strategy chain
(WordPress Tribe REST → Squarespace JSON → iCal → JSON-LD → …), then, if
nothing structured is found:

  * the generic listing reader (utils/generic_listing.py) when the entry says
    `heuristic: true` — only set after the venue's output was checked by hand;
  * the LLM reader (utils/llm_extract.py) — needs ANTHROPIC_API_KEY.

To add a venue: add it to public/data/venues.json, then add an entry here.
A venue that later outgrows this gets its own module in scrapers/venues/ and
its entry removed (a venue must have exactly one scraper — see registry.py).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..base import BaseScraper

CONFIG = Path(__file__).resolve().parents[1] / "generic_venues.yaml"
_FIELDS = ("events_url", "exhibitions_url", "ical_url", "feed_url", "wp_root",
           "eventbrite_url", "default_event_type", "heuristic", "url_must_contain",
           "llm_fallback", "squarespace")


VENUES = Path(__file__).resolve().parents[2] / "public" / "data" / "venues.json"


def build() -> list[type]:
    import json
    try:
        rows = {v["id"]: v for v in json.loads(VENUES.read_text(encoding="utf-8"))}
    except (OSError, ValueError) as e:
        print(f"  [generic] could not read venues.json: {e}")
        return []
    try:
        entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"  [generic] could not read {CONFIG.name}: {e}")
        return []
    classes = []
    for vid, cfg in (entries.get("venues") or {}).items():
        cfg = dict(cfg or {})
        row = rows.get(vid)
        if row is None:
            print(f"  [generic] {vid} is not in venues.json — skipped")
            continue
        cfg.setdefault("events_url", row.get("events_url") or row.get("website"))
        if row.get("exhibitions_url"):
            cfg.setdefault("exhibitions_url", row["exhibitions_url"])
        if not cfg.get("events_url"):
            continue
        attrs = {"venue_id": vid, "source_label": cfg.get("source_label", "")}
        for k in _FIELDS:
            if k in cfg:
                attrs[k] = cfg[k]
        classes.append(type(f"Generic_{vid}", (BaseScraper,), attrs))
    return classes
