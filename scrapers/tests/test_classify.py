"""Classification: the raw harvest in, the published listing out.

The property that matters most here is RETROACTIVITY — a change to rules.yaml
must re-label events scraped months ago, not just future ones. Before the
raw/derived split, an event's type was frozen at scrape time and a taxonomy
change could never reach the archive.
"""
from datetime import date, timedelta

from scrapers.classify import derive, relabel

SOON = (date.today() + timedelta(days=90)).isoformat()
LONG_AGO = (date.today() - timedelta(days=400)).isoformat()


def _raw(**kw):
    base = {
        "id": "e1", "venue_id": "test", "title": "Artist Talk: Someone",
        "description": "", "event_type": "other", "event_types": ["other"],
        "start": SOON, "end": None,
        "_default_type": "other",
    }
    base.update(kw)
    return base


# ── Re-derivation ─────────────────────────────────────────────────────────

def test_type_is_recomputed_from_the_text():
    """A stored label that the text contradicts is corrected, not trusted."""
    out = relabel(_raw(title="Artist Talk: Someone", event_type="other"))
    assert out["event_type"] == "lecture"


def test_a_venue_asserted_type_beats_text_inference():
    """Getty publishes its own category; that is better evidence than the title.

    Without this, re-classification would silently discard the venue's own
    knowledge and re-guess every event from its wording.
    """
    out = relabel(_raw(title="Some Ambiguous Title", _asserted_type="performance"))
    assert out["event_type"] == "performance"


def test_an_asserted_type_that_no_longer_exists_falls_back_to_the_text():
    """If you retire a type in rules.yaml, old records must not keep a dead label."""
    out = relabel(_raw(title="Artist Talk: Someone", _asserted_type="rave"))
    assert out["event_type"] == "lecture"


def test_exhibitions_stay_exhibitions():
    out = relabel(_raw(title="Sixty Years of Prints", event_type="exhibition"))
    assert out["event_type"] == "exhibition"
    assert out["event_types"] == ["exhibition"]


def test_secondary_types_are_collected():
    """An event can be filtered under several types."""
    out = relabel(_raw(title="Screening and Artist Talk: The Film"))
    assert "screening" in out["event_types"]
    assert "lecture" in out["event_types"]


def test_corrupted_text_is_repaired_during_relabel():
    out = relabel(_raw(title="Instante/revelaciÃ³n"))
    assert out["title"] == "Instante/revelación"


# ── The whole pipeline ────────────────────────────────────────────────────

def test_derive_separates_upcoming_from_archive():
    result = derive([
        _raw(id="future", start=SOON),
        _raw(id="past", start=LONG_AGO),
    ])
    assert [e["id"] for e in result.upcoming] == ["future"]
    assert [e["id"] for e in result.archive] == ["past"]


def test_derive_never_invents_or_duplicates_events():
    raw = [_raw(id=f"e{i}", start=(date.today() + timedelta(days=30 + i * 10)).isoformat()) for i in range(5)]
    result = derive(raw)
    produced = {e["id"] for e in result.upcoming} | {e["id"] for e in result.archive}
    assert produced <= {e["id"] for e in raw}
    ids = [e["id"] for e in result.upcoming]
    assert len(ids) == len(set(ids)), "an event appears twice in the output"


def test_derive_is_deterministic():
    """The same harvest must always produce the same listing, in the same order.

    Otherwise every daily commit is full of spurious reordering and a real
    change becomes impossible to spot in the diff.
    """
    raw = [_raw(id=f"e{i}", title=f"Event {i}",
                start=(date.today() + timedelta(days=30 + i * 10)).isoformat()) for i in range(5)]
    first = derive(raw).upcoming
    second = derive(list(reversed(raw))).upcoming
    assert [e["id"] for e in first] == [e["id"] for e in second]


def test_a_rules_change_reaches_events_scraped_long_ago():
    """The whole point of storing the raw harvest.

    We simulate a taxonomy change by relabelling an old record and checking the
    new label sticks — proving classification reads the rules at derive time
    rather than trusting whatever was stored.
    """
    old_record = _raw(id="old", title="Printmaking Workshop: Sun Prints",
                      event_type="other", event_types=["other"])
    out = relabel(old_record)
    assert out["event_type"] == "workshop", (
        "an event stored with a stale label must pick up the current rules"
    )
