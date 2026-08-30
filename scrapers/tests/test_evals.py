"""The health-check suite itself.

The suite exists to catch problems in the scrapers. These catch problems in the
suite — because a check that always says "fine" and a system that is genuinely
fine look identical from the outside, and only one of them is good news.
"""
from datetime import date, timedelta

from scrapers.evals import faults, integrity, selftest
from scrapers.evals.model import FAIL, PASS, SKIP, WARN, Finding, worst

SOON = (date.today() + timedelta(days=60)).isoformat()


def _ev(**kw):
    base = {"id": "e1", "venue_id": "lacma", "title": "A Real Event",
            "description": "", "event_type": "lecture", "start": SOON}
    base.update(kw)
    return base


VENUES = [{"id": "lacma", "events_url": "https://www.lacma.org/event"}]


# ── The headline verdict ──────────────────────────────────────────────────

def test_a_check_that_could_not_run_is_not_reported_as_a_failure():
    """'We could not check X' is different news from 'X is broken'."""
    findings = [Finding("a", "q", PASS, ""), Finding("b", "q", SKIP, "")]
    assert worst(findings) == PASS


def test_a_real_failure_still_wins_the_headline():
    findings = [Finding("a", "q", PASS, ""), Finding("b", "q", WARN, ""),
                Finding("c", "q", FAIL, "")]
    assert worst(findings) == FAIL


# ── The self-test can catch planted faults ────────────────────────────────

def test_the_suite_notices_faults_planted_under_its_nose():
    """If this fails, no other result from the suite can be believed."""
    findings = selftest.run([_ev()], VENUES, offline=True)
    assert findings[0].verdict == PASS, findings[0].evidence


# ── The safety equipment is armed ─────────────────────────────────────────

def test_the_fault_injection_group_reports_armed_protections():
    findings = faults.run()
    for f in findings:
        assert f.verdict == PASS, f"{f.id}: {f.evidence}"


# ── Individual checks catch their own subject ─────────────────────────────

def test_garbled_text_is_caught():
    found = integrity.quality([_ev(title="Instante/revelaciÃ³n")], VENUES)
    assert next(f for f in found if f.id == "E1").verdict == FAIL


def test_clean_text_is_not_flagged():
    found = integrity.quality([_ev(title="Instante/revelación")], VENUES)
    assert next(f for f in found if f.id == "E1").verdict == PASS


def test_an_event_pointing_at_an_unknown_venue_is_caught():
    found = integrity.quality([_ev(venue_id="nowhere")], VENUES)
    assert next(f for f in found if f.id == "E3").verdict == FAIL


def test_a_shrinking_archive_is_caught():
    previous = {"events": 100, "archive": 700, "by_venue": {}, "upcoming_ids": [],
                "future_ids": []}
    found = integrity.drift([_ev()], [{"id": "a"}], previous)
    assert next(f for f in found if f.id == "B1").verdict == FAIL


def test_a_growing_archive_is_fine():
    previous = {"events": 1, "archive": 1, "by_venue": {}, "upcoming_ids": [],
                "future_ids": []}
    found = integrity.drift([_ev()], [{"id": "a"}, {"id": "b"}], previous)
    assert next(f for f in found if f.id == "B1").verdict == PASS


def test_the_monitor_calling_a_dead_venue_healthy_is_caught():
    status = {"venues": [{"venue_id": "ghost", "verdict": "green", "events": 0,
                          "exhibitions": 0, "reasons": []}],
              "counts": {"green": 1, "yellow": 0, "red": 0}}
    found = integrity.monitoring(status, [_ev()], {})
    assert next(f for f in found if f.id == "D1").verdict == FAIL


def test_a_snapshot_records_what_the_next_run_needs():
    snap = integrity.snapshot([_ev()], [{"id": "a"}])
    assert snap["events"] == 1 and snap["archive"] == 1
    assert "e1" in snap["upcoming_ids"]
    assert "e1" in snap["future_ids"], "an event 60 days out should be tracked as future"
