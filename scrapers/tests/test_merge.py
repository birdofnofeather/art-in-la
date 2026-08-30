"""How a fresh harvest merges into the stored one.

The rule that matters: a venue's UPCOMING records are replaced by the new
scrape (so a cancelled event disappears), but its PAST records are kept
forever. A venue's website stops listing an event once it has happened, so a
past record can never be re-harvested — dropping it deletes history.

Getting this wrong took the archive from 757 records to 203 in one run.
"""
from datetime import datetime, timedelta, timezone

from scrapers.run_all import prune_raw, RAW_RETENTION_DAYS

NOW = datetime.now(timezone.utc)


def _rec(vid, eid, days_from_now):
    when = (NOW + timedelta(days=days_from_now)).isoformat()
    return {"id": eid, "venue_id": vid, "title": eid, "start": when, "end": when}


def _merge(existing, fresh):
    """The merge rule from run_all.main, isolated so it can be tested."""
    from scrapers.run_all import _end_of
    from scrapers.utils.dedupe import dedupe
    producing = {e["venue_id"] for e in fresh if e.get("venue_id")}
    carryover = []
    for ev in existing:
        if ev.get("venue_id") not in producing:
            carryover.append(ev)
            continue
        end = _end_of(ev)
        if end is not None and end < NOW:
            carryover.append(ev)
    return dedupe(carryover + fresh)


def test_past_records_survive_a_rescrape_of_their_venue():
    existing = [_rec("hammer", "old", -30), _rec("hammer", "stale-upcoming", +10)]
    fresh = [_rec("hammer", "new", +20)]
    ids = {e["id"] for e in _merge(existing, fresh)}
    assert "old" in ids, "history must never be deleted by a rescrape"
    assert "new" in ids


def test_upcoming_records_are_replaced_not_accumulated():
    """A cancelled event must disappear once the venue stops listing it."""
    existing = [_rec("hammer", "cancelled", +10)]
    fresh = [_rec("hammer", "still-on", +20)]
    ids = {e["id"] for e in _merge(existing, fresh)}
    assert "cancelled" not in ids
    assert "still-on" in ids


def test_a_venue_that_produced_nothing_keeps_everything():
    """A broken scraper must not wipe that venue from the site."""
    existing = [_rec("sciarc", "a", +10), _rec("sciarc", "b", -10)]
    fresh = [_rec("hammer", "c", +5)]
    ids = {e["id"] for e in _merge(existing, fresh)}
    assert {"a", "b", "c"} == ids


def test_pruning_drops_only_records_older_than_the_retention_window():
    keep_recent = _rec("v", "recent", -10)
    keep_future = _rec("v", "future", +10)
    drop_ancient = _rec("v", "ancient", -(RAW_RETENTION_DAYS + 30))
    ids = {e["id"] for e in prune_raw([keep_recent, keep_future, drop_ancient])}
    assert ids == {"recent", "future"}


def test_pruning_keeps_a_record_with_no_usable_date():
    """Undated records are handled by the hygiene gate, not silently binned here."""
    undated = {"id": "u", "venue_id": "v", "title": "u", "start": None, "end": None}
    assert [e["id"] for e in prune_raw([undated])] == ["u"]
