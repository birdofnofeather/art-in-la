"""Recurring-programme detection, using the real cases from the live data.

Every test here is a bug that actually shipped, or a correct behaviour that a
future change could plausibly break.
"""
from datetime import date, timedelta

from scrapers.utils.recurring import (
    filter_recurring, has_regular_cadence, is_recurring_by_keyword,
)


def _ev(venue, title, start, eid=None):
    return {
        "id": eid or f"{venue}-{title}-{start}",
        "venue_id": venue,
        "title": title,
        "description": "",
        "start": str(start),
        "event_type": "other",
    }


def _weekly(venue, title, n, start=None, step=7):
    first = start or date(2026, 9, 4)
    return [_ev(venue, title, first + timedelta(days=step * i)) for i in range(n)]


# ── The bug this rewrite exists for ───────────────────────────────────────

def test_pieter_weekly_class_with_only_four_dates_is_hidden():
    """The exact record that leaked: 4 occurrences, under the old threshold of 5.

    A weekly class with four dates left on the calendar is still a weekly class.
    Counting occurrences could never catch this; spacing does.
    """
    events = _weekly("pieter", "Queerchata: Intro to Bachata", 4)
    kept, dropped = filter_recurring(events)
    assert kept == [], "a weekly class must not reach the calendar"
    assert len(dropped) == 4


def test_a_three_night_theatre_run_stays_visible():
    """REDCAT's 'The Ford/Hill Project' ran three consecutive nights.

    Three consecutive dates are perfectly evenly spaced, so a naive rhythm check
    hides them — but this is a real show people buy tickets for.
    """
    events = _weekly("redcat", "The Ford/Hill Project", 3, step=1)
    kept, _ = filter_recurring(events)
    assert len(kept) == 3, "a consecutive-night run is an event, not a programme"


def test_two_occurrences_alone_are_not_a_series():
    """Two dates cannot establish a rhythm — a show and its repeat is not clutter."""
    events = _weekly("hammer", "An Evening With The Artist", 2)
    kept, _ = filter_recurring(events)
    assert len(kept) == 2


def test_many_repeats_are_a_series_even_when_irregular():
    """A programme running at scattered intervals is still a programme."""
    first = date(2026, 9, 1)
    offsets = [0, 5, 9, 20, 26, 40, 55]
    events = [_ev("wende", "Writing Group", first + timedelta(days=o)) for o in offsets]
    kept, dropped = filter_recurring(events)
    assert kept == [], "seven repeats is a standing programme however it is spaced"
    assert len(dropped) == len(offsets)


# ── The deliberate exclusions (see rules.yaml) ────────────────────────────

def test_deliberate_exclusions_stay_excluded():
    """Getty, LACMA, Norton Simon and Huntington standing programmes."""
    for title in [
        "Art, Architecture, and Garden Tour",
        "Gallery Tour: Modern Art",
        "Docent-Led Highlights Tour",
        "Introductory Film",
        "Daily Meditation in the Garden",
        "K-12 Educators Virtual Office Hours",
    ]:
        assert is_recurring_by_keyword(title), f"{title!r} should be hidden"


def test_real_one_off_events_are_never_hidden_by_name():
    """These must survive — hiding them would be a regression, not a tidy-up."""
    for title in [
        "Curator's Tour: Instante/revelación",
        "Artist Talk: Sadie Barnette",
        "Opening Reception: New Work",
        "Mid-Autumn Moon Celebration",
        "Screening: Daughters of the Dust",
    ]:
        assert not is_recurring_by_keyword(title), f"{title!r} must stay visible"


# ── Collapsing ────────────────────────────────────────────────────────────

def test_a_curators_tour_series_collapses_to_one_listing():
    """Worth listing once, not four times — and the other dates are noted."""
    events = _weekly("getty_center", "Curator's Tour: Odilon Redon", 4)
    kept, dropped = filter_recurring(events)
    assert len(kept) == 1, "a curator's tour series should collapse, not vanish"
    assert len(dropped) == 3
    assert kept[0].get("recurrence_count") == 4
    assert "Also on" in kept[0].get("recurrence_note", "")


def test_venue_override_forces_a_drop():
    """Pieter's whole calendar is classes, so its series are dropped outright."""
    events = _weekly("pieter", "Curator's Tour: Something", 4)
    kept, _ = filter_recurring(events)
    assert kept == [], "the pieter override must beat the collapse pattern"


# ── The cadence primitive ─────────────────────────────────────────────────

def test_cadence_requires_a_real_gap():
    daily = [date(2026, 9, 1) + timedelta(days=i) for i in range(4)]
    weekly = [date(2026, 9, 1) + timedelta(days=7 * i) for i in range(4)]
    assert not has_regular_cadence(daily, 2, 3), "consecutive days are a run"
    assert has_regular_cadence(weekly, 2, 3), "weekly spacing is a programme"


def test_cadence_ignores_absurdly_long_gaps():
    yearly = [date(2024, 9, 1), date(2025, 9, 1), date(2026, 9, 1)]
    assert not has_regular_cadence(yearly, 2, 3), "an annual event is not clutter"


def test_recurring_filter_never_invents_events():
    events = _weekly("pieter", "Some Class", 5) + _weekly("hammer", "A Real Talk", 2)
    kept, dropped = filter_recurring(events)
    assert len(kept) + len(dropped) >= len(events)
    kept_ids = {e["id"] for e in kept}
    assert kept_ids <= {e["id"] for e in events}, "output contains an event that was never input"
