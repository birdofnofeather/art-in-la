"""Group G — can these checks actually detect a problem?

The trap this exists for: on the first full run, every single check passed. That
is either very good news or completely worthless information, and from the
outside the two look identical. A check with a bug that makes it always return
"fine" is invisible precisely on the days you need it.

So this group takes the real published data, deliberately breaks a copy of it
in a specific way, and confirms the relevant check notices. If a check cannot
spot a fault planted directly under its nose, its passing verdict on the real
data means nothing and should not be believed.

This runs on every eval cycle, not once. A check can be broken by a later
change just as easily as it can be born broken.
"""
from __future__ import annotations

from datetime import date, timedelta

from .model import Finding, PASS, FAIL
from . import integrity, truth

FUTURE = (date.today() + timedelta(days=45)).isoformat()
LONG_PAST = (date.today() - timedelta(days=30)).isoformat()


def _base_event(**kw) -> dict:
    ev = {
        "id": "self-test-1", "venue_id": "lacma", "title": "A Perfectly Normal Event",
        "description": "", "event_type": "lecture", "start": FUTURE, "end": None,
        "url": "https://www.lacma.org/event", "scraped_at": FUTURE,
    }
    ev.update(kw)
    return ev


def run(events: list[dict], venues: list[dict], offline: bool = False) -> list[Finding]:
    """Plant a fault, confirm the check finds it. Never touches the real files."""
    trials: list[tuple[str, bool, str]] = []
    known_venue_ids = {v["id"] for v in venues if v.get("id")}

    # ── Can we still spot garbled text? ──────────────────────────────────
    poisoned = list(events) + [_base_event(id="st-mojibake",
                                           title="Instante/revelaciÃ³n")]
    found = integrity.quality(poisoned, venues)
    e1 = next(f for f in found if f.id == "E1")
    trials.append(("garbled text (E1)", e1.verdict == FAIL,
                   "planted an event with corrupted accents"))

    # ── Can we still spot the same event listed twice? ───────────────────
    dupe = _base_event(id="st-dupe")
    poisoned = list(events) + [dupe, dict(dupe)]
    found = integrity.quality(poisoned, venues)
    e2 = next(f for f in found if f.id == "E2")
    trials.append(("duplicate events (E2)", e2.verdict == FAIL,
                   "planted the same event id twice"))

    # ── Can we still spot an event with no venue? ────────────────────────
    orphan = _base_event(id="st-orphan", venue_id="a_venue_that_does_not_exist")
    found = integrity.quality(list(events) + [orphan], venues)
    e3 = next(f for f in found if f.id == "E3")
    trials.append(("events with no venue (E3)", e3.verdict == FAIL,
                   "planted an event pointing at a venue that isn't in the list"))

    # ── Can we still spot an event that already happened? ────────────────
    stale = _base_event(id="st-stale", start=LONG_PAST, end=LONG_PAST)
    found = integrity.quality(list(events) + [stale], venues)
    e4 = next(f for f in found if f.id == "E4")
    trials.append(("events already over (E4)", e4.verdict == FAIL,
                   "planted an event that finished a month ago"))

    # ── Can we still spot an event with no date? ─────────────────────────
    undated = _base_event(id="st-undated", start=None)
    found = integrity.quality(list(events) + [undated], venues)
    e5 = next(f for f in found if f.id == "E5")
    trials.append(("events with no date (E5)", e5.verdict == FAIL,
                   "planted an event with no start date"))

    # ── Can we still spot a weekly programme leaking through? ────────────
    weekly = [_base_event(id=f"st-weekly-{i}", title="A Weekly Standing Class",
                          start=(date.today() + timedelta(days=30 + 7 * i)).isoformat())
              for i in range(4)]
    found = integrity.quality(list(events) + weekly, venues)
    e7 = next(f for f in found if f.id == "E7")
    trials.append(("recurring programmes leaking (E7)", e7.verdict != PASS,
                   "planted four copies of one title, a week apart"))

    # ── Can we still spot the monitor lying about a venue? ───────────────
    fake_status = {
        "venues": [{"venue_id": "a_silent_venue", "verdict": "green",
                    "events": 0, "exhibitions": 0, "reasons": []}],
        "counts": {"green": 1, "yellow": 0, "red": 0},
    }
    found = integrity.monitoring(fake_status, events, {})
    d1 = next(f for f in found if f.id == "D1")
    trials.append(("the monitor calling a dead venue healthy (D1)", d1.verdict == FAIL,
                   "planted a status report claiming a venue with no events is green"))

    # ── Can we still spot a made-up event? (needs the internet) ──────────
    if offline:
        trials.append(("fabricated events (A1)", True,
                       "skipped — this run was told not to use the internet"))
    else:
        real_url = next((e.get("url") for e in events if e.get("url")), None)
        if real_url:
            invented = _base_event(
                id="st-fabricated", url=real_url,
                title="Zorblat Quintessence Fandango Of The Nonexistent Wibble",
            )
            checked = truth.sample_and_verify([invented], size=1)
            caught = bool(checked) and checked[0]["reachable"] and not checked[0]["title_found"]
            trials.append((
                "fabricated events (A1)", caught,
                "planted an event whose title appears nowhere on the page it links to",
            ))
        else:
            trials.append(("fabricated events (A1)", False,
                           "no published event has a link, so this could not be tested"))

    passed = [t for t in trials if t[1]]
    return [Finding(
        "G1", "Can these checks still detect a problem when there is one?",
        PASS if len(passed) == len(trials) else FAIL,
        (f"{len(passed)} of {len(trials)} deliberately planted faults were caught. "
         f"This is the check on the checks. Every other result in this report is "
         f"only worth reading if this one passes — a check with a bug that makes "
         f"it always say 'fine' looks exactly like a system that is fine, right "
         f"up until the day it is not."),
        evidence=[f"MISSED: {t[0]} — {t[2]}" for t in trials if not t[1]]
                 or [f"caught: {t[0]}" for t in trials],
        independent=False,
        numbers={"faults_planted": len(trials), "faults_caught": len(passed)},
    )]
