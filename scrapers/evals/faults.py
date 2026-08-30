"""Group C — is the safety equipment actually armed?

Every protective check in this project has a problem: it has never fired. The
fleet gate has blocked exactly zero publishes. The quality rules have caught
nothing since the day the corrupted Getty text was cleaned up. Untested safety
equipment is indistinguishable from broken safety equipment — a smoke alarm you
have never tested and a smoke alarm with a dead battery look exactly the same
from the outside, right up until the fire.

So these checks deliberately break things and confirm the system objects.

Each one builds a fake, obviously-wrong version of the data, hands it to the
real protective code, and fails the eval if that code shrugs and lets it
through. Nothing here touches the real data or the live site.

This is the group most likely to catch a change that silently disarms a
protection — someone loosening a threshold, an exception being swallowed, a
check accidentally short-circuiting. Those changes never announce themselves,
and no ordinary test notices, because the everyday path still works.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..utils import fleet
from ..utils.recurring import filter_recurring, is_recurring_by_keyword
from ..utils.text import normalise
from ..utils.validate import quality_report, validate
from .model import Finding, PASS, FAIL

SOON = (date.today() + timedelta(days=60)).isoformat()


def _events(n: int, venue: str = "v", prefix: str = "e") -> list[dict]:
    return [{"id": f"{prefix}{i}", "venue_id": venue, "title": f"Event {i}",
             "description": "", "event_type": "lecture", "start": SOON}
            for i in range(n)]


def _expect_blocked(name: str, result) -> tuple[bool, str]:
    if result.ok:
        return False, f"{name}: the gate ALLOWED it through — this protection is not working"
    return True, f"{name}: blocked, as it should be"


def run() -> list[Finding]:
    findings: list[Finding] = []
    checks: list[tuple[str, bool, str]] = []

    # ── The fleet gate ───────────────────────────────────────────────────
    # Half the events vanishing overnight.
    ok, msg = _expect_blocked(
        "a sudden 75% collapse in the event count",
        fleet.check(_events(100), _events(400), [], []))
    checks.append(("fleet", ok, msg))

    # The archive shrinking. Past events can never be re-scraped, so this is
    # the one kind of data loss that is permanent.
    ok, msg = _expect_blocked(
        "the archive of past events shrinking",
        fleet.check(_events(100), _events(100), _events(200, prefix="a"),
                    _events(757, prefix="a")))
    checks.append(("fleet", ok, msg))

    # The same event listed many times.
    dupes = [{"id": "same", "venue_id": "v", "title": "T",
              "event_type": "lecture", "start": SOON} for _ in range(4)]
    ok, msg = _expect_blocked("the same event id repeated four times",
                              fleet.check(dupes, _events(4), [], []))
    checks.append(("fleet", ok, msg))

    # Many venues going dark together — our bug, not theirs.
    before = [{"id": f"e{i}", "venue_id": f"v{i}", "title": "T",
               "event_type": "lecture", "start": SOON} for i in range(12)]
    after = [before[0]]
    ok, msg = _expect_blocked("eleven venues going silent at once",
                              fleet.check(after, before, [], []))
    checks.append(("fleet", ok, msg))

    # An empty run.
    ok, msg = _expect_blocked("a run that produced nothing at all",
                              fleet.check([], _events(400), [], []))
    checks.append(("fleet", ok, msg))

    # Events with no date, which cannot be placed on a calendar.
    undated = [{"id": "u", "venue_id": "v", "title": "T",
                "event_type": "lecture", "start": None}]
    ok, msg = _expect_blocked("an event with no date at all",
                              fleet.check(undated, _events(1), [], []))
    checks.append(("fleet", ok, msg))

    # And the opposite: an ordinary day must NOT be blocked. A gate that
    # blocks everything is just as broken as one that blocks nothing, and
    # would freeze the site on a permanently stale copy.
    ordinary = fleet.check(_events(390), _events(400), _events(600, prefix="a"),
                           _events(600, prefix="a"))
    checks.append(("fleet", ordinary.ok,
                   "an ordinary day with a 2.5% change: "
                   + ("published, as it should be" if ordinary.ok
                      else "BLOCKED — the gate is too strict and would freeze the site")))

    passed = [c for c in checks if c[1]]
    findings.append(Finding(
        "C1", "Does the safety gate still refuse to publish obviously broken data?",
        PASS if len(passed) == len(checks) else FAIL,
        (f"{len(passed)} of {len(checks)} deliberate faults behaved correctly. "
         f"This is the check that proves the protection is switched on: it feeds "
         f"the real gate a broken day and confirms it objects, and feeds it a "
         f"normal day and confirms it does not."),
        evidence=[c[2] for c in checks if not c[1]] or [c[2] for c in checks[:2]],
        numbers={"faults_tested": len(checks), "behaved_correctly": len(passed)},
    ))

    # ── The text-quality rules ───────────────────────────────────────────
    quality: list[tuple[bool, str]] = []

    repaired = normalise("Instante/revelaciÃ³n")
    quality.append((repaired == "Instante/revelación",
                    f"corrupted Spanish repaired to {repaired!r}"))

    kept, _ = validate([{"id": "q", "venue_id": "v", "event_type": "lecture",
                         "title": "Instante/revelaciÃ³n", "description": "",
                         "start": SOON}])
    quality.append((len(kept) == 1 and "ó" in kept[0]["title"],
                    "an event with repairable corruption is fixed, not thrown away"))

    blocking, _ = quality_report({"id": "q", "venue_id": "v", "title": "A <br> B",
                                  "event_type": "lecture", "start": SOON})
    quality.append((bool(blocking), "leftover page markup in a title is refused"))

    blocking, _ = quality_report({"id": "q", "venue_id": "", "title": "Real Event",
                                  "event_type": "lecture", "start": SOON})
    quality.append((bool(blocking), "an event with no venue is refused"))

    blocking, reportable = quality_report({"id": "q", "venue_id": "v",
                                           "title": "Ãdouard Manet",
                                           "event_type": "lecture", "start": SOON})
    quality.append((not blocking and bool(reportable),
                    "damage we cannot repair is reported but the event is kept"))

    q_passed = [q for q in quality if q[0]]
    findings.append(Finding(
        "C2", "Do the text-quality rules still catch unreadable text?",
        PASS if len(q_passed) == len(quality) else FAIL,
        (f"{len(q_passed)} of {len(quality)} text faults behaved correctly. These "
         f"are the rules that were missing when six Getty events sat on the live "
         f"site reading 'espaÃ±ol' for weeks with nothing complaining."),
        evidence=[q[1] for q in quality if not q[0]] or ["all text rules armed"],
        numbers={"faults_tested": len(quality), "behaved_correctly": len(q_passed)},
    ))

    # ── The deliberate curation decisions ────────────────────────────────
    # These must survive forever. The easiest way to make a venue's numbers
    # look better is to weaken these, and that would be a silent regression.
    curation: list[tuple[bool, str]] = []

    for title in ["Art, Architecture, and Garden Tour",   # Getty
                  "Gallery Tour: Modern Art",             # LACMA
                  "Docent-Led Highlights Tour",
                  "Introductory Film",                    # Norton Simon
                  "K-12 Educators Virtual Office Hours"]: # Huntington
        curation.append((is_recurring_by_keyword(title),
                         f"{title!r} is still hidden"))

    for title in ["Curator's Tour: Instante/revelación",
                  "Artist Talk: Sadie Barnette",
                  "Mid-Autumn Moon Celebration"]:
        curation.append((not is_recurring_by_keyword(title),
                         f"{title!r} is still visible"))

    # Pieter's weekly classes: four dates, seven days apart.
    weekly = [{"id": f"p{i}", "venue_id": "pieter", "description": "",
               "title": "Queerchata: Intro to Bachata", "event_type": "workshop",
               "start": (date.today() + timedelta(days=14 + 7 * i)).isoformat()}
              for i in range(4)]
    kept, _ = filter_recurring(weekly)
    curation.append((kept == [], "Pieter's weekly dance classes are still hidden"))

    # A three-night theatre run must NOT be hidden.
    run_nights = [{"id": f"r{i}", "venue_id": "redcat", "description": "",
                   "title": "The Ford/Hill Project", "event_type": "performance",
                   "start": (date.today() + timedelta(days=20 + i)).isoformat()}
                  for i in range(3)]
    kept, _ = filter_recurring(run_nights)
    curation.append((len(kept) == 3, "a three-night theatre run is still visible"))

    # A long-running exhibition must never be mistaken for a weekly programme.
    shows = [{"id": f"x{i}", "venue_id": "moca_grand", "description": "",
              "title": f"Show {i}", "event_type": "exhibition",
              "event_types": ["exhibition"], "start": SOON, "end": SOON}
             for i in range(12)]
    kept, _ = filter_recurring(shows)
    curation.append((len(kept) == 12, "long-running exhibitions are still visible"))

    c_passed = [c for c in curation if c[0]]
    findings.append(Finding(
        "C3", "Are the curation decisions you made on purpose still holding?",
        PASS if len(c_passed) == len(curation) else FAIL,
        (f"{len(c_passed)} of {len(curation)} deliberate decisions still behave as "
         f"intended. The easiest way to make a venue's event count look healthier "
         f"is to weaken one of these, so they are checked explicitly rather than "
         f"trusted."),
        evidence=[c[1] for c in curation if not c[0]] or ["every decision holding"],
        numbers={"decisions_tested": len(curation), "holding": len(c_passed)},
    ))

    return findings
