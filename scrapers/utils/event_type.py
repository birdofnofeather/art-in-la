"""Event-type classification, driven entirely by scrapers/rules.yaml.

There are deliberately no keywords in this file. Every decision about what
counts as a tour, a workshop or an opening lives in the rules file so it can be
changed without touching code — and so a change is checked against the examples
recorded alongside it.
"""
from __future__ import annotations

from .rules import load
from .text import normalise


def allowed() -> set[str]:
    """Every event type id the rules currently define."""
    return set(load().type_ids)


def _text(title: str, description: str = "") -> str:
    return normalise(f"{title or ''} \n {description or ''}")


def infer(title: str, description: str = "", default: str = "other") -> str:
    """The PRIMARY type: the first rule (in file order) whose pattern matches.

    Falls back to `default` (a per-venue setting, e.g. Academy Museum defaults
    to 'screening') and then to 'other'.
    """
    rules = load()
    text = _text(title, description)
    for rule in rules.event_types:
        if rule.patterns and rule.matches(text):
            return rule.id
    return default if default in allowed() else "other"


def infer_all(title: str, description: str = "") -> list[str]:
    """Every type whose pattern matches, in rules-file order.

    An event that reads as both a performance and a screening comes back as
    both so it can be filtered under either.
    """
    rules = load()
    text = _text(title, description)
    return [r.id for r in rules.event_types if r.patterns and r.matches(text)]
