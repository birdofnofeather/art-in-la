"""Audience tagging, driven by scrapers/rules.yaml.

Marks events aimed at families/kids or teens/youth so the front-end can offer a
"Family-friendly" filter. The patterns live in the rules file; to add a tag,
add a block under `audience:` there — no code change needed.
"""
from __future__ import annotations

import re

from .rules import load
from .text import normalise

# Guard against the incidental possessive ("the artist's family", "his family"),
# which is a property of English rather than a curation decision, so it stays in
# code rather than cluttering the rules file.
_POSSESSIVE_BEFORE = re.compile(r"(?:'s|s')\s+$")


def infer(title: str, description: str = "") -> list[str]:
    rules = load()
    text = normalise(f"{title or ''} \n {description or ''}")
    out = []
    for tag, patterns in rules.audience.items():
        for pattern in patterns:
            m = pattern.search(text)
            if m and not _POSSESSIVE_BEFORE.search(text[max(0, m.start() - 4):m.start()]):
                out.append(tag)
                break
    return out
