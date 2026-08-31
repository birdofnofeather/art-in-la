"""Does the system actually know when it is working?

Each test is a failure the old monitoring could not see, or a false alarm that
would make a new monitor useless. The second kind matters as much as the first:
a monitor that cries wolf every day trains you to ignore it, which is worse
than having none.
"""
from scrapers.monitor import GREEN, RED, YELLOW, assess, assess_venue
from scrapers.utils import fleet


def _ev(vid="lacma", etype="lecture", **kw):
    base = {"id": "x", "venue_id": vid, "title": "An Event",
            "event_type": etype, "start": "2026-12-01"}
    base.update(kw)
    return base


# ── Witness 1: the venue's own page ───────────────────────────────────────

def test_a_page_full_of_dates_and_nothing_extracted_is_red():
    r = assess_venue("x", produced=[], published=[], health={}, expectation={},
                     dates_on_page=24)
    assert r["verdict"] == RED
    assert "extracted nothing" in " ".join(r["reasons"])


def test_curation_hiding_events_is_not_treated_as_breakage():
    """Pieter's page advertises 47 dates; we publish 4 on purpose.

    Witness 1 must compare against what we HARVESTED, not what we published,
    or every well-curated venue is flagged as broken every single day.
    """
    harvested = [_ev("pieter") for _ in range(47)]
    published = [_ev("pieter") for _ in range(4)]
    r = assess_venue("pieter", produced=harvested, published=published,
                     health={}, expectation={}, dates_on_page=47)
    assert r["verdict"] == GREEN, r["reasons"]


def test_a_sparse_page_does_not_trigger_the_page_comparison():
    """A venue with genuinely little on must not be accused of a broken parser.

    This checks WITNESS 1 specifically. The venue is still flagged — it is
    publishing nothing, and "green" has to mean we verified it works — but the
    reason must not claim its parser is missing events the page is showing,
    because the page is not showing any.
    """
    r = assess_venue("x", produced=[], published=[], health={}, expectation={},
                     dates_on_page=2)
    assert not any("advertises" in reason for reason in r["reasons"]), (
        "witness 1 must stay silent when the page has almost nothing on it"
    )
    assert r["verdict"] != RED


# ── Triage: their problem vs ours ─────────────────────────────────────────

def test_an_unreachable_website_is_not_reported_as_our_bug():
    """Several venues block datacenter addresses and work fine from elsewhere.

    Sending an automated repair at a scraper whose site is simply refusing us
    produces confident, wrong changes to code that was never broken.
    """
    health = {"zero_streak": 12, "last_success": "2026-07-01"}
    r = assess_venue("norton_simon", produced=[], published=[], health=health,
                     expectation={}, dates_on_page=None, unreachable=True)
    assert r["verdict"] == YELLOW, "an unreachable site is not a broken parser"
    assert "not our parser" in " ".join(r["reasons"])


def test_a_reachable_site_producing_nothing_is_our_bug():
    health = {"zero_streak": 12, "last_success": "2026-07-01"}
    r = assess_venue("sciarc", produced=[], published=[], health=health,
                     expectation={}, dates_on_page=None, unreachable=False)
    assert r["verdict"] == RED


# ── Witness 3: the written expectation ────────────────────────────────────

def test_a_venue_with_events_but_no_exhibitions_is_flagged():
    """The failure nothing could see before.

    LACMA published 4 events and 0 exhibitions for months and looked healthy,
    because the only question asked was whether the count was zero.
    """
    published = [_ev("lacma") for _ in range(4)]
    r = assess_venue("lacma", produced=published, published=published, health={},
                     expectation={"min_exhibitions": 8}, dates_on_page=None)
    assert r["verdict"] == YELLOW
    assert "exhibitions" in " ".join(r["reasons"])


def test_a_venue_meeting_its_expectation_is_green():
    published = [_ev("lacma") for _ in range(6)] + \
                [_ev("lacma", etype="exhibition") for _ in range(9)]
    r = assess_venue("lacma", produced=published, published=published, health={},
                     expectation={"min_events": 2, "max_events": 20, "min_exhibitions": 8},
                     dates_on_page=None)
    assert r["verdict"] == GREEN, r["reasons"]


# ── Witness 2: drift against recent history ───────────────────────────────

def test_a_collapse_short_of_zero_is_still_caught():
    """40 events becoming 3 never trips a zero check, but is plainly broken."""
    published = [_ev("armory") for _ in range(3)]
    r = assess_venue("armory", produced=published, published=published,
                     health={"recent_counts": [40, 42, 41, 39]},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] == YELLOW
    assert "below its recent average" in " ".join(r["reasons"])


def test_normal_variation_is_not_flagged():
    published = [_ev("x") for _ in range(9)]
    r = assess_venue("x", produced=published, published=published,
                     health={"recent_counts": [10, 11, 9, 12]},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] == GREEN


# ── The fleet gate ────────────────────────────────────────────────────────

def _many(n, vid="v"):
    return [_ev(vid, id=f"e{i}") | {"id": f"e{i}"} for i in range(n)]


def test_a_catastrophic_drop_blocks_publishing():
    before, after = _many(400), _many(100)
    r = fleet.check(after, before, [], [])
    assert not r.ok
    assert "too large to be a real day's change" in " ".join(r.blocking)


def test_an_ordinary_day_publishes():
    before, after = _many(400), _many(390)
    assert fleet.check(after, before, [], []).ok


def test_an_empty_run_never_publishes():
    assert not fleet.check([], _many(400), [], []).ok


def test_a_shrinking_archive_blocks_publishing():
    """Past events cannot be re-scraped, so losing them is unrecoverable.

    This is the check that would have caught the merge bug that took the
    archive from 757 records to 203 in one run.
    """
    r = fleet.check(_many(100), _many(100), _many(200), _many(757))
    assert not r.ok
    assert "archive shrank" in " ".join(r.blocking)


def test_duplicate_ids_block_publishing():
    dupes = [_ev(id="same") | {"id": "same"} for _ in range(3)]
    r = fleet.check(dupes, _many(3), [], [])
    assert not r.ok
    assert "duplicate" in " ".join(r.blocking)


def test_many_venues_going_dark_at_once_blocks_publishing():
    """One venue breaking is their site. Ten at once is our pipeline."""
    before = [_ev(f"v{i}", id=f"e{i}") | {"id": f"e{i}", "venue_id": f"v{i}"}
              for i in range(12)]
    after = [_ev("v0", id="e0") | {"id": "e0", "venue_id": "v0"}]
    r = fleet.check(after, before, [], [])
    assert not r.ok
    assert "points at our pipeline" in " ".join(r.blocking)


def test_a_growing_event_count_warns_but_still_publishes():
    """A rise might be a parser eating the navigation, but it is not dangerous."""
    r = fleet.check(_many(600), _many(400), [], [])
    assert r.ok
    assert r.warnings


def test_the_fleet_verdict_reflects_how_many_venues_are_broken():
    published = [_ev("a"), _ev("b")]
    venues = [{"id": "a", "events_url": "http://a"}, {"id": "b", "events_url": "http://b"}]
    report = assess(published, health={}, venues=venues, expectations={},
                    probe=False, scraped_ids=["a", "b"])
    assert report["verdict"] == GREEN
    assert report["totals"]["events"] == 2


# ── Found by the eval suite, 2026-08-30 ───────────────────────────────────

def test_a_venue_that_publishes_nothing_is_never_green():
    """LMU's Laband Gallery sat green while showing visitors nothing.

    It harvested events fine, so the source-page check was satisfied and its
    zero-streak stayed at zero for the same reason — but every record was
    filtered out before publication. Whether that is correct or a bug, 'green'
    is the wrong answer to both.
    """
    harvested = [_ev("laband") for _ in range(6)]
    r = assess_venue("laband", produced=harvested, published=[], health={},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] != GREEN
    assert "published none" in " ".join(r["reasons"])


def test_a_known_gap_is_counted_but_does_not_shout_every_day():
    """Fifteen venues repeating the same known news is how a report becomes noise."""
    published = [_ev("lacma") for _ in range(4)]
    expectation = {"min_exhibitions": 8, "known_gap": "exhibitions"}
    r = assess_venue("lacma", produced=published, published=published, health={},
                     expectation=expectation, dates_on_page=None)
    assert r["verdict"] == GREEN, "a tracked, accepted gap must not raise a daily flag"
    assert "exhibitions" in r["known_gaps"], "...but it must still be counted"


def test_an_untracked_exhibition_shortfall_still_raises_a_flag():
    """Only gaps we have deliberately acknowledged go quiet."""
    published = [_ev("somewhere") for _ in range(4)]
    r = assess_venue("somewhere", produced=published, published=published, health={},
                     expectation={"min_exhibitions": 5}, dates_on_page=None)
    assert r["verdict"] == YELLOW


def test_drift_is_not_judged_from_a_two_day_history():
    """Twelve venues were flagged for drifting from an average two days old."""
    published = [_ev("x") for _ in range(3)]
    r = assess_venue("x", produced=published, published=published,
                     health={"recent_counts": [40, 41]},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] == GREEN, "two data points is not a trend"


def test_drift_is_judged_once_there_is_a_real_baseline():
    published = [_ev("x") for _ in range(3)]
    r = assess_venue("x", produced=published, published=published,
                     health={"recent_counts": [40, 41, 39, 42, 40]},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] == YELLOW


def test_a_venue_showing_visitors_nothing_is_never_green():
    """Museum of Tolerance sat green while its page on the site was empty.

    It landed just under every threshold at once: two silent runs where the
    alarm needs three, no upcoming dates on its own page so the page comparison
    declined to judge, and nothing harvested that run so the "harvested but
    published none" check did not apply. Every witness declined, and silence
    read as health.

    "Green" must mean "we checked and it works", not "we found no evidence
    either way".
    """
    r = assess_venue("museum_of_tolerance", produced=[], published=[],
                     health={"zero_streak": 2, "last_success": "2026-08-30"},
                     expectation={}, dates_on_page=0)
    assert r["verdict"] == YELLOW
    assert "nothing on the site" in " ".join(r["reasons"])


def test_a_quiet_venue_says_so_rather_than_implying_a_fault():
    """If the venue's own page has nothing on either, say that plainly."""
    r = assess_venue("somewhere", produced=[], published=[], health={},
                     expectation={}, dates_on_page=0)
    assert "quiet period" in " ".join(r["reasons"])


def test_a_venue_that_publishes_events_is_unaffected():
    published = [_ev("lacma") for _ in range(4)]
    r = assess_venue("lacma", produced=published, published=published, health={},
                     expectation={}, dates_on_page=None)
    assert r["verdict"] == GREEN
