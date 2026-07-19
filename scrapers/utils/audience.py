"""Audience tagging from free text.

Marks events aimed at families/kids or teens/youth so the front-end can offer a
"Family-friendly" filter — the single highest-propensity museum-going segment.
"""
from __future__ import annotations

import re

# Require a family/kids signal but avoid the incidental possessive
# ("the artist's family", "his family") by disallowing a preceding possessive.
_FAMILY = re.compile(
    r"(?<!'s )(?<!s' )\b("
    r"family|families|kids?|children|childrens|"
    r"all[- ]ages|toddlers?|preschool|little\s+ones|story\s?time|story\s+hour|"
    r"sensory[- ]friendly"
    r")\b",
    re.I,
)
_TEEN = re.compile(r"\b(teens?|teenagers?|youth|high[- ]school|young\s+adults?)\b", re.I)


def infer(title: str, description: str = "") -> list[str]:
    text = f"{title or ''} \n {description or ''}"
    out = []
    if _FAMILY.search(text):
        out.append("family")
    if _TEEN.search(text):
        out.append("teen")
    return out
