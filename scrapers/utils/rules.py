"""Loads scrapers/rules.yaml — the single source of truth for curation policy.

Everything that decides *what counts as what* lives in that YAML file, not in
Python. This module just reads it, compiles the regexes once, and hands back
plain objects. If you want to change a decision, edit the YAML.

Design note: nothing here is allowed to fail silently. A malformed rules file
raises at import time rather than quietly reverting to some hidden default,
because a silently-ignored curation rule is exactly the failure mode this
whole design exists to prevent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.yaml"


class RulesError(RuntimeError):
    """The rules file is missing, malformed, or internally inconsistent."""


@dataclass
class EventTypeRule:
    id: str
    label: str
    patterns: list[re.Pattern] = field(default_factory=list)
    examples_match: list[str] = field(default_factory=list)
    examples_reject: list[str] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)


@dataclass
class ForbiddenText:
    id: str
    pattern: re.Pattern
    says: str
    severity: str = "drop"      # "drop" = never publish; "warn" = publish + report


@dataclass
class Rules:
    version: int
    event_types: list[EventTypeRule]
    # recurring
    recurring_drop: list[re.Pattern]
    recurring_drop_examples: tuple[list[str], list[str]]
    recurring_collapse: list[re.Pattern]
    cadence_min_occurrences: int
    cadence_tolerance_days: int
    cadence_min_gap_days: int
    cadence_max_gap_days: int
    cadence_absolute_threshold: int
    recurring_default_action: str
    recurring_venue_overrides: dict[str, str]
    # exhibitions
    exh_min_duration_hours: int
    exh_max_duration_days: int
    exh_undated_grace_days: int
    exh_never: list[re.Pattern]
    exh_never_promote_types: set[str]
    exh_examples: tuple[list[str], list[str]]
    # audience
    audience: dict[str, list[re.Pattern]]
    audience_examples: dict[str, tuple[list[str], list[str]]]
    # quality
    forbid_in_text: list[ForbiddenText]
    required_fields: list[str]
    require_start_unless_exhibition: bool
    max_days_in_future: int
    max_days_in_past: int
    min_title_length: int

    @property
    def type_ids(self) -> list[str]:
        return [t.id for t in self.event_types]

    def type_label(self, type_id: str) -> str:
        for t in self.event_types:
            if t.id == type_id:
                return t.label
        return type_id


def _compile(patterns, where: str) -> list[re.Pattern]:
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            raise RulesError(f"rules.yaml → {where}: bad pattern {p!r}: {e}") from e
    return out


def _examples(block: dict) -> tuple[list[str], list[str]]:
    ex = (block or {}).get("examples") or {}
    return list(ex.get("match") or []), list(ex.get("reject") or [])


def _load(path: Path) -> Rules:
    if not path.exists():
        raise RulesError(f"rules file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise RulesError(f"rules.yaml is not valid YAML: {e}") from e
    if not isinstance(raw, dict):
        raise RulesError("rules.yaml must be a mapping at the top level")

    # ── event types ──────────────────────────────────────────────────────
    types_raw = raw.get("event_types") or []
    if not types_raw:
        raise RulesError("rules.yaml defines no event_types")
    event_types = []
    seen = set()
    for block in types_raw:
        tid = block.get("id")
        if not tid:
            raise RulesError("an event_types entry has no id")
        if tid in seen:
            raise RulesError(f"duplicate event type id: {tid}")
        seen.add(tid)
        m, r = _examples(block)
        event_types.append(EventTypeRule(
            id=tid,
            label=block.get("label") or tid.title(),
            patterns=_compile(block.get("patterns"), f"event_types.{tid}"),
            examples_match=m,
            examples_reject=r,
        ))
    if "other" not in seen:
        raise RulesError("rules.yaml must define an 'other' event type as the fallback")

    # ── recurring ────────────────────────────────────────────────────────
    rec = raw.get("recurring") or {}
    cad = rec.get("cadence") or {}
    overrides = {}
    for vid, block in (rec.get("venue_overrides") or {}).items():
        action = (block or {}).get("action", "drop")
        if action not in ("drop", "collapse", "keep"):
            raise RulesError(f"recurring.venue_overrides.{vid}.action must be drop/collapse/keep")
        overrides[vid] = action

    default_action = rec.get("default_action", "drop")
    if default_action not in ("drop", "collapse", "keep"):
        raise RulesError("recurring.default_action must be drop/collapse/keep")

    # ── exhibitions ──────────────────────────────────────────────────────
    exh = raw.get("exhibitions") or {}

    # ── audience ─────────────────────────────────────────────────────────
    aud_raw = raw.get("audience") or {}
    audience, audience_examples = {}, {}
    for tag, block in aud_raw.items():
        audience[tag] = _compile((block or {}).get("patterns"), f"audience.{tag}")
        audience_examples[tag] = _examples(block)

    # ── quality ──────────────────────────────────────────────────────────
    q = raw.get("quality") or {}
    forbid = []
    for block in q.get("forbid_in_text") or []:
        severity = block.get("severity", "drop")
        if severity not in ("drop", "warn"):
            raise RulesError(
                f"quality.forbid_in_text.{block.get('id')}: severity must be 'drop' or 'warn'"
            )
        forbid.append(ForbiddenText(
            id=block.get("id") or "unnamed",
            pattern=_compile([block["pattern"]], "quality.forbid_in_text")[0],
            says=block.get("says") or "",
            severity=severity,
        ))

    return Rules(
        version=int(raw.get("version", 1)),
        event_types=event_types,
        recurring_drop=_compile(rec.get("drop_patterns"), "recurring.drop_patterns"),
        recurring_drop_examples=_examples(rec),
        recurring_collapse=_compile(rec.get("collapse_patterns"), "recurring.collapse_patterns"),
        cadence_min_occurrences=int(cad.get("min_occurrences", 3)),
        cadence_tolerance_days=int(cad.get("tolerance_days", 2)),
        cadence_min_gap_days=int(cad.get("min_gap_days", 3)),
        cadence_max_gap_days=int(cad.get("max_gap_days", 45)),
        cadence_absolute_threshold=int(cad.get("absolute_threshold", 6)),
        recurring_default_action=default_action,
        recurring_venue_overrides=overrides,
        exh_min_duration_hours=int(exh.get("min_duration_hours", 36)),
        exh_max_duration_days=int(exh.get("max_duration_days", 550)),
        exh_undated_grace_days=int(exh.get("undated_grace_days", 45)),
        exh_never=_compile(exh.get("never_patterns"), "exhibitions.never_patterns"),
        exh_never_promote_types=set(exh.get("never_promote_types") or []),
        exh_examples=_examples(exh),
        audience=audience,
        audience_examples=audience_examples,
        forbid_in_text=forbid,
        required_fields=list(q.get("required_fields") or ["id", "venue_id", "title"]),
        require_start_unless_exhibition=bool(q.get("require_start_unless_exhibition", True)),
        max_days_in_future=int(q.get("max_days_in_future", 550)),
        max_days_in_past=int(q.get("max_days_in_past", 1)),
        min_title_length=int(q.get("min_title_length", 3)),
    )


@lru_cache(maxsize=1)
def load() -> Rules:
    """Read and cache the rules. Raises RulesError if the file is unusable."""
    return _load(RULES_PATH)


def reload() -> Rules:
    """Force a re-read — used by tests and by `reclassify` after an edit."""
    load.cache_clear()
    return load()
