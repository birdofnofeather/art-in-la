"""Heuristics for inferring an event_type from free text."""
from __future__ import annotations

import re

ALLOWED = {
    "opening", "closing", "exhibition", "workshop", "lecture",
    "performance", "screening", "tour", "fair", "other",
}

KEYWORDS = [
    # Opening/closing first: an "opening reception" is an opening, not a party.
    ("opening",     r"\b(opening|preview|vernissage|reception)\b"),
    ("closing",     r"\b(closing|finissage|last\s+day|final\s+day)\b"),
    ("screening",   r"\b(screenings?|films?|movies?|cinema|documentary|shorts?\s+program)\b"),
    ("performance", r"\b(performances?|concerts?|recitals?|dance|dj|live\s+music|music|theater|theatre|cabaret)\b"),
    ("workshop",    r"\b(workshops?|classes?|class|hands[- ]on|drop[- ]in|art[- ]?making|makers?|camps?|craft|printmaking|studio\s+session)\b"),
    ("lecture",     r"\b(lectures?|talks?|conversations?|in\s+conversation|panel|symposium|seminar|reading|poetry|book\s+(?:talk|launch|signing|club)|artist\s+talk|q\s?&\s?a)\b"),
    ("tour",        r"\b(tours?|guided\s+walks?|walk[- ]?through|docent)\b"),
    ("fair",        r"\b(fair|art\s?week|biennial|festival|celebration|block\s+party|family\s+day|open\s+house|open\s+studios?|gala|market|fest)\b"),
    ("exhibition",  r"\b(exhibitions?|on\s+view|installations?)\b"),
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

