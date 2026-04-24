"""Heuristics for inferring an event_type from free text."""
from __future__ import annotations

import re

ALLOWED = {
    "opening", "closing", "exhibition", "workshop", "lecture",
    "performance", "screening", "tour", "fair", "other",
}

KEYWORDS = [
    ("opening",     r"\b(opening|preview|vernissage)\b"),
    ("closing",     r"\b(closing|finissage|last day)\b"),
    ("workshop",    r"\b(workshop|class|hands[- ]on|drop[- ]in)\b"),
    ("lecture",     r"\b(lecture|talk|conversation|panel|symposium|reading|book launch)\b"),
    ("performance", r"\b(performance|concert|recital|dance|music)\b"),
    ("screening",   r"\b(screening|film|movie|cinema)\b"),
    ("tour",        r"\b(tour|guided walk)\b"),
    ("fair",        r"\b(fair|art week|biennial)\b"),
    ("exhibition",  r"\b(exhibition|on view|show|installation)\b"),
]


def infer(title: str, description: str = "", default: str = "other") -> str:
    """Guess an event type from text. Returns one of ALLOWED."""
    text = f"{title or ''} \n {description or ''}".lower()
    for kind, pattern in KEYWORDS:
        if re.search(pattern, text):
            return kind
    return default if default in ALLOWED else "other"
