"""Recurring-programme detection.

A standing programme — a weekly dance class, a daily docent tour — is clutter
on a calendar people use to plan a trip. This module finds them.

Two mechanisms, both configured in scrapers/rules.yaml:

  (a) BY NAME. The title matches one of `recurring.drop_patterns`. These are the
      deliberate exclusions (Getty's garden tour, LACMA's gallery tours,
      Huntington's standing programmes) and they are always dropped.

  (b) BY RHYTHM. The same title appears several times at regular intervals.

Why rhythm and not counting: the previous version dropped a title only when it
appeared 5+ times. Pieter's "Queerchata: Intro to Bachata" appears exactly 4
times — a weekly class with four dates left on the calendar — and sailed
straight through, along with 78 other records fleet-wide. How many dates happen
to remain in the scrape window says nothing about whether something recurs.
Even spacing does.

A series caught by rhythm is either dropped or COLLAPSED (keep the next
occurrence, note the rest on it), depending on the rules file. Collapsing is
right for something like a curator's tour tied to a specific exhibition: worth
listing once, not four times.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .rules import load
from .text import title_key


def _is_exhibition(ev: dict) -> bool:
    return (ev.get("event_type") == "exhibition") or (
        "exhibition" in (ev.get("event_types") or [])
    )


# ── Name matching ─────────────────────────────────────────────────────────

def is_recurring_by_keyword(title: str, description: str = "") -> bool:
    """True if the title/description names a known standing programme."""
    rules = load()
    text = f"{title or ''} \n {description or ''}"
    return any(p.search(text) for p in rules.recurring_drop)


def _should_collapse(title: str) -> bool:
    rules = load()
    return any(p.search(title or "") for p in rules.recurring_collapse)


# ── Rhythm detection ──────────────────────────────────────────────────────

def _as_date(raw):
    """Parse a stored start value to a date, or None."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.date()


def has_regular_cadence(dates: list, tolerance_days: int, min_occurrences: int,
                        min_gap_days: int = 3, max_gap_days: int = 45) -> bool:
    """True if these dates are evenly spaced — the signature of a standing series.

    Needs at least `min_occurrences` distinct dates, whose consecutive gaps all
    agree to within `tolerance_days` and all fall between `min_gap_days` and
    `max_gap_days`.

    The lower bound is the important one. Three performances on three
    consecutive nights are perfectly evenly spaced, but that is a theatre run —
    a real event people buy tickets for — not a standing programme. Requiring a
    gap of at least a few days keeps runs visible while still catching the
    weekly, fortnightly and monthly programmes that are genuine clutter.
    """
    uniq = sorted({d for d in dates if d is not None})
    if len(uniq) < max(2, min_occurrences):
        return False
    gaps = [(b - a).days for a, b in zip(uniq, uniq[1:])]
    if not gaps or min(gaps) < min_gap_days or max(gaps) > max_gap_days:
        return False
    return (max(gaps) - min(gaps)) <= tolerance_days


# ── Main entry point ──────────────────────────────────────────────────────

def filter_recurring(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (kept, dropped).

    Pass 1 — drop anything whose name matches a standing-programme pattern.
    Pass 2 — group what's left by (venue, title); drop or collapse any group
             that recurs on a regular rhythm, or that simply repeats a lot.
    """
    rules = load()
    kept: list[dict] = []
    dropped: list[dict] = []

    # Exhibitions are exempt from everything below. An exhibition is a date
    # RANGE, not a repeated occurrence — "on view for 31 days" is not "happens
    # every week". Without this exemption a long-running show is mistaken for a
    # standing programme and vanishes from the site, which is how MOCA's
    # MONUMENTS and four other shows disappeared.
    exhibitions = [e for e in events if _is_exhibition(e)]
    candidates = [e for e in events if not _is_exhibition(e)]

    # ── Pass 1: by name ───────────────────────────────────────────────────
    for ev in candidates:
        if is_recurring_by_keyword(ev.get("title", ""), ev.get("description", "")):
            dropped.append(ev)
        else:
            kept.append(ev)

    # ── Pass 2: by rhythm ─────────────────────────────────────────────────
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for ev in kept:
        groups[(ev.get("venue_id", ""), title_key(ev.get("title", "")))].append(ev)

    final: list[dict] = []
    for (venue_id, _key), members in groups.items():
        # An explicit per-venue setting is a deliberate decision about that
        # venue and beats the general collapse patterns. Only when a venue has
        # no override do we let a title's wording choose collapse over drop.
        explicit = venue_id in rules.recurring_venue_overrides
        action = rules.recurring_venue_overrides.get(venue_id, rules.recurring_default_action)
        if action == "keep" or len(members) < 2:
            final.extend(members)
            continue

        dates = [_as_date(m.get("start")) for m in members]
        is_series = (
            len(members) >= rules.cadence_absolute_threshold
            or has_regular_cadence(dates, rules.cadence_tolerance_days,
                                   rules.cadence_min_occurrences,
                                   rules.cadence_min_gap_days,
                                   rules.cadence_max_gap_days)
        )
        if not is_series:
            final.extend(members)
            continue

        # A series the rules say to keep once, rather than hide entirely.
        collapse = action == "collapse" or (
            not explicit and _should_collapse(members[0].get("title", ""))
        )
        if collapse:
            ordered = sorted(
                members,
                key=lambda m: (_as_date(m.get("start")) or datetime.max.date()),
            )
            survivor = dict(ordered[0])
            others = [_as_date(m.get("start")) for m in ordered[1:]]
            more = [d.strftime("%b %-d") for d in others if d]
            if more:
                survivor["recurrence_note"] = "Also on " + ", ".join(more[:6])
            survivor["recurrence_count"] = len(ordered)
            final.append(survivor)
            dropped.extend(ordered[1:])
        else:
            dropped.extend(members)

    # Exhibitions were never candidates; put them back.
    final.extend(exhibitions)

    # Stable output: the caller sorts, but keep it deterministic regardless.
    final.sort(key=lambda e: (str(e.get("start") or ""), e.get("title") or ""))
    return final, dropped
