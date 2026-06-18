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
    ("workshop",    r"\b(workshops?|classes?|class|hands[- ]on|drop[- ]in)\b"),
    ("lecture",     r"\b(lectures?|talks?|conversations?|panel|symposium|reading|book launch)\b"),
    ("performance", r"\b(performances?|concerts?|recitals?|dance|music)\b"),
    ("screening",   r"\b(screenings?|films?|movies?|cinema)\b"),
    ("tour",        r"\b(tours?|guided walks?)\b"),
    ("fair",        r"\b(fair|art week|biennial)\b"),
    ("exhibition",  r"\b(exhibitions?|on view|installations?)\b"),
]


def infer(title: str, description: str = "", default: str = "other") -> str:
    """Guess an event type from text. Returns one of ALLOWED."""
    text = f"{title or ''} \n {description or ''}".lower()
    for kind, pattern in KEYWORDS:
        if re.search(pattern, text):
            return kind
    return default if default in ALLOWED else "other"


def infer_all(title: str, description: str = "") -> list[str]:
    """Return every event type whose keywords appear in the text, in priority
    order. An event that reads as both a performance and a screening comes back
    as ["performance", "screening"] so it can be filtered under either.
    """
    text = f"{title or ''} \n {description or ''}".lower()
    return [kind for kind, pattern in KEYWORDS if re.search(pattern, text)]

