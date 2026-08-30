#!/usr/bin/env python3
"""Check scrapers/rules.yaml against the examples written inside it.

Every rule in the rules file carries examples: `match:` lists titles it SHOULD
catch, `reject:` lists titles it must NOT catch. This runs them all.

Why this exists: the single most tempting way to "fix" a venue whose event count
has dropped is to weaken the recurring filter, which would quietly undo
deliberate exclusions — Getty's garden tour, LACMA's gallery tours, Huntington's
standing programmes. The reject examples make that impossible to do by accident,
whether the person doing it is you or an automated repair.

    python -m scrapers.check_rules

Exit code 0 = every example behaves as written. Non-zero = something changed.
"""
from __future__ import annotations

import sys

from .utils.event_type import infer
from .utils.recurring import is_recurring_by_keyword
from .utils.rules import reload as reload_rules
from .utils.audience import infer as infer_audience


def _report(failures: list[str], checked: int) -> int:
    print()
    if failures:
        print(f"✗ {len(failures)} of {checked} examples behave differently than written:\n")
        for f in failures:
            print(f"    {f}")
        print("\nEither the rule needs fixing, or the example is out of date and")
        print("should be updated deliberately — not deleted to make this pass.")
        return 1
    print(f"✓ all {checked} examples in rules.yaml behave as written")
    return 0


def check() -> int:
    try:
        rules = reload_rules()
    except Exception as e:
        print(f"✗ rules.yaml could not be loaded: {e}", file=sys.stderr)
        return 2

    failures: list[str] = []
    checked = 0

    # ── Event types ───────────────────────────────────────────────────────
    # A `match` example must classify as its own type. A `reject` example must
    # not — though it may legitimately land on another type.
    for rule in rules.event_types:
        for title in rule.examples_match:
            checked += 1
            got = infer(title)
            if got != rule.id:
                failures.append(
                    f"event type '{rule.id}': expected {rule.id!r} for {title!r}, got {got!r}"
                )
        for title in rule.examples_reject:
            checked += 1
            if rule.matches(title.lower()):
                failures.append(
                    f"event type '{rule.id}': should NOT match {title!r}, but its pattern does"
                )

    # ── Recurring: the deliberate exclusions ─────────────────────────────
    drop_match, drop_reject = rules.recurring_drop_examples
    for title in drop_match:
        checked += 1
        if not is_recurring_by_keyword(title):
            failures.append(f"recurring: {title!r} should be hidden as a standing programme, but is not")
    for title in drop_reject:
        checked += 1
        if is_recurring_by_keyword(title):
            failures.append(
                f"recurring: {title!r} is a real one-off event and must stay visible, "
                f"but a drop pattern hides it"
            )

    # ── Exhibitions ───────────────────────────────────────────────────────
    exh_match, exh_reject = rules.exh_examples
    for title in exh_match:
        checked += 1
        if any(p.search(title) for p in rules.exh_never):
            failures.append(f"exhibitions: {title!r} is a real show but a never_pattern excludes it")
    for title in exh_reject:
        checked += 1
        if not any(p.search(title) for p in rules.exh_never):
            failures.append(f"exhibitions: {title!r} should be excluded by a never_pattern, but is not")

    # ── Audience ──────────────────────────────────────────────────────────
    for tag, (yes, no) in rules.audience_examples.items():
        for title in yes:
            checked += 1
            if tag not in infer_audience(title):
                failures.append(f"audience '{tag}': expected tag on {title!r}, got {infer_audience(title)}")
        for title in no:
            checked += 1
            if tag in infer_audience(title):
                failures.append(f"audience '{tag}': should NOT tag {title!r}, but does")

    print(f"Checked rules v{rules.version}: {len(rules.event_types)} event types, "
          f"{len(rules.recurring_drop)} always-drop patterns, "
          f"{len(rules.audience)} audience tags.")
    return _report(failures, checked)


if __name__ == "__main__":
    sys.exit(check())
