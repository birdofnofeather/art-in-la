"""Recurring-event detection and filtering.

Two mechanisms:
1. Keyword match – title or description signals a standing recurring program
   (daily/weekly/every <weekday>, In Focus Tour, Gallery Tour, Docent-led, etc.)
2. Frequency dedup – same normalised title appears REPEAT_THRESHOLD+ times
   from the same venue → it's a standing series; drop all occurrences.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

# ── Keyword pattern ────────────────────────────────────────────────────────────
_RECURRING_KW = re.compile(
    r"""
    \b(
        daily | weekly |
        every\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|day) |
        (?:mondays|tuesdays|wednesdays|thursdays|fridays|saturdays|sundays)\b |

        # Common recurring tour-series patterns (museum / gallery programmes)
        in\s+focus\s+tour |
        gallery\s+tour |
        exhibition\s+highlights?\s+tour |
        guided\s+tour |
        collection\s+tour |
        architecture\s+(?:and\s+garden\s+)?tour |
        curator'?s\s+gallery\s+tour |
        docent          # covers "docent-led", "docent tour", etc.
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ── Threshold ──────────────────────────────────────────────────────────────────
# If the same (venue_id, normalised_title) pair appears this many times in the
# upcoming events list, treat it as a standing series and drop all occurrences.
REPEAT_THRESHOLD = 5


# ── Public helpers ─────────────────────────────────────────────────────────────

def is_recurring_by_keyword(title: str, description: str = "") -> bool:
    """Return True if title/description matches a known recurring-programme pattern."""
    return bool(
        _RECURRING_KW.search(title or "")
        or _RECURRING_KW.search(description or "")
    )


def _norm(title: str) -> str:
    return title.strip().lower()


def filter_recurring(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (kept, dropped) after filtering recurring standing programmes.

    Pass 1 – keyword filter.
    Pass 2 – frequency dedup (same title ≥ REPEAT_THRESHOLD times per venue).
    """
    kept: list[dict] = []
    dropped: list[dict] = []

    # Pass 1: keyword
    for ev in events:
        if is_recurring_by_keyword(ev.get("title", ""), ev.get("description", "")):
            dropped.append(ev)
        else:
            kept.append(ev)

    # Pass 2: frequency
    counts: dict[str, Counter] = defaultdict(Counter)
    for ev in kept:
        counts[ev.get("venue_id", "")][_norm(ev.get("title", ""))] += 1

    recurring_pairs: set[tuple[str, str]] = {
        (vid, t)
        for vid, c in counts.items()
        for t, n in c.items()
        if n >= REPEAT_THRESHOLD
    }

    if not recurring_pairs:
        return kept, dropped

    final: list[dict] = []
    for ev in kept:
        key = (ev.get("venue_id", ""), _norm(ev.get("title", "")))
        if key in recurring_pairs:
            dropped.append(ev)
        else:
            final.append(ev)

    return final, dropped
