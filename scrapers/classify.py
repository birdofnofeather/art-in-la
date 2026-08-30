"""Turn the raw harvest into the published listing.

This is the second half of the pipeline, and keeping it separate from scraping
is the point. Scraping is per-venue code that talks to websites. Classification
is policy: what an event is called, which recurring programmes are hidden, what
counts as an exhibition, what is clean enough to publish. All of that comes
from scrapers/rules.yaml.

Because the raw harvest is stored untouched in public/data/raw_events.json,
you can change a rule and re-derive EVERYTHING — including the archive — in a
couple of seconds without re-scraping a single website:

    python -m scrapers.reclassify

Before this split, an event's type was decided once at scrape time and frozen
into the data forever, so changing the taxonomy could only ever affect events
scraped afterwards. Now a rules change is retroactive.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .utils.archive import split
from .utils.audience import infer as infer_audience
from .utils.dedupe import dedupe
from .utils.event_type import infer as infer_type, infer_all as infer_types, allowed as allowed_types
from .utils.recurring import filter_recurring
from .utils.text import normalise
from .utils.validate import validate, quality_issues


@dataclass
class Derived:
    """Everything the publish step needs, plus the accounting to explain it."""
    upcoming: list[dict] = field(default_factory=list)
    archive: list[dict] = field(default_factory=list)
    dropped_recurring: list[dict] = field(default_factory=list)
    dropped_hygiene: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "upcoming": len(self.upcoming),
            "archive": len(self.archive),
            "dropped_recurring": len(self.dropped_recurring),
            "dropped_hygiene": len(self.dropped_hygiene),
        }


def relabel(ev: dict) -> dict:
    """Re-derive everything policy decides, from the raw text.

    Deliberately recomputed rather than trusted from storage: this is what makes
    a rules.yaml edit apply to events that were scraped months ago.
    """
    out = dict(ev)
    out["title"] = normalise(out.get("title") or "")
    out["description"] = normalise(out.get("description") or "")

    title, desc = out["title"], out.get("description") or ""
    default_type = out.get("_default_type") or "other"
    asserted = out.get("_asserted_type")

    # An exhibition stays an exhibition: that decision is made during scraping
    # from the event's duration and the venue's own markup, not from wording.
    if out.get("event_type") == "exhibition" or asserted == "exhibition":
        out["event_type"] = "exhibition"
        out["event_types"] = ["exhibition"]
    else:
        # A type the venue itself published beats anything we can guess from
        # the title — but only while it is still a type the rules recognise.
        # If you retire a type in rules.yaml, records carrying it fall back to
        # being read from their text instead of keeping a label that no longer
        # exists.
        if asserted and asserted in allowed_types():
            primary = asserted
        else:
            primary = infer_type(title, desc, default=default_type)
        types = [primary]
        for t in infer_types(title, desc):
            if t != "exhibition" and t not in types:
                types.append(t)
        out["event_type"] = primary
        out["event_types"] = types

    out["audience"] = infer_audience(title, desc)
    return out


def derive(raw_events: list[dict], now=None) -> Derived:
    """Raw harvest in, publishable listing out.

    Order matters:
      1. relabel   — apply the current taxonomy to every record
      2. dedupe    — one record per event, keeping the richest version
      3. recurring — hide standing programmes (by name, then by rhythm)
      4. archive   — move anything already finished out of the live list
      5. validate  — structural and quality gate on what's left
    """
    labelled = [relabel(ev) for ev in raw_events]
    combined = dedupe(labelled)

    kept, dropped_recurring = filter_recurring(combined)

    upcoming, past = split(kept)
    upcoming, dropped_hygiene = validate(upcoming, now=now)

    # The archive gets the same quality treatment, minus the "already ended"
    # rule that every archived event would trip by definition.
    clean_archive = [ev for ev in past if not quality_issues(ev)]

    return Derived(
        upcoming=upcoming,
        archive=dedupe(clean_archive),
        dropped_recurring=dropped_recurring,
        dropped_hygiene=dropped_hygiene,
    )
