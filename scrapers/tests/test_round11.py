"""Tests for Round 11: generic listing reader, LLM validation, production runs."""
from datetime import date

from scrapers.utils import generic_listing as gl
from scrapers.utils import llm_extract as llm
from scrapers.utils.runs import collapse_runs, _base

TODAY = date(2026, 11, 5)


# ── generic listing reader ─────────────────────────────────────────────────
def test_parse_dates_variants():
    assert gl.parse_dates("Nov 14, 2026 7 PM", TODAY) == (date(2026, 11, 14), None, "19:00")
    assert gl.parse_dates("Saturday, December 6 · 7:30pm", TODAY)[0] == date(2026, 12, 6)
    s, e, _ = gl.parse_dates("November 20 – 22", TODAY)
    assert (s, e) == (date(2026, 11, 20), date(2026, 11, 22))
    s, e, _ = gl.parse_dates("Nov 20 – Jan 10, 2027", TODAY)
    assert (s, e) == (date(2026, 11, 20), date(2027, 1, 10))
    assert gl.parse_dates("no date here", TODAY) is None


CARDS = """<html><body><nav><a href="/events">Events</a> Nov 1, 2026</nav><main>
<div class="card"><h3><a href="/e/one">Artist Talk: Jane Doe</a></h3><p>Thursday, November 12, 2026 · 7 PM</p></div>
<div class="card"><h3><a href="/e/two">Read More</a></h3><p>December 3</p></div>
<div class="card"><h3><a href="/e/old">Old Summer Concert</a></h3><p>August 22</p><p>Summer 2026 series</p></div>
<div class="card"><h3><a href="/e/x">Gone Show 2022</a></h3><p>Nov 20</p></div>
</main></body></html>"""


def test_extract_cards_and_guards():
    items = gl.extract(CARDS, "https://v.org/events", today=TODAY)
    titles = [i["title"] for i in items]
    assert "Artist Talk: Jane Doe" in titles
    talk = items[titles.index("Artist Talk: Jane Doe")]
    assert talk["url"] == "https://v.org/e/one" and talk["time"] == "19:00"
    assert "Read More" not in titles                 # junk title
    assert "Old Summer Concert" not in titles        # past, year-less → not pushed to next year
    assert "Gone Show 2022" not in titles            # card names only past years


# ── LLM output validation (no network) ─────────────────────────────────────
PAGE = "Upcoming\nArtist Talk: Jane Doe <https://v.org/e/1>\nThursday, November 12 at 7pm\nFree\n"


def test_llm_validation_keeps_supported_items():
    items = [{"title": "Artist Talk: Jane Doe", "kind": "event", "start_date": "2026-11-12",
              "end_date": None, "start_time": "19:00", "url": "https://v.org/e/1",
              "price_text": "Free", "description": None}]
    out = llm.validate_items(items, PAGE, today=TODAY)
    assert len(out) == 1 and out[0]["time"] == "19:00"


def test_llm_validation_rejects_hallucinations():
    bad = [
        {"title": "Invented Gala", "kind": "event", "start_date": "2026-11-12", "end_date": None,
         "start_time": None, "url": None, "price_text": None, "description": None},     # not on page
        {"title": "Artist Talk: Jane Doe", "kind": "event", "start_date": "2026-11-19", "end_date": None,
         "start_time": None, "url": None, "price_text": None, "description": None},     # day 19 not on page
        {"title": "Artist Talk: Jane Doe", "kind": "event", "start_date": "2025-11-12", "end_date": None,
         "start_time": None, "url": None, "price_text": None, "description": None},     # in the past
        {"title": "Artist Talk: Jane Doe", "kind": "event", "start_date": "Nov 12", "end_date": None,
         "start_time": "7pm", "url": None, "price_text": None, "description": None},    # bad formats
    ]
    assert llm.validate_items(bad, PAGE, today=TODAY) == []


def test_llm_disabled_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.extract_listing("v", "V", "https://v.org", html="<p>x</p>") == []
    assert llm.recover([{"title": "t", "url": "https://v.org"}]) == []


# ── production runs ────────────────────────────────────────────────────────
def _ev(title, start, vid="theater"):
    return {"venue_id": vid, "title": title, "start": start, "end": None,
            "event_type": "performance", "event_types": ["performance"], "url": "u"}


def test_base_title_keeps_real_parentheses():
    assert _base("SOFT MAGICAL TOFU BOY(S) (New Works Festival)") == "SOFT MAGICAL TOFU BOY(S)"
    assert _base("KRISTINA WONG #FoodBankInfluencer (Opening Night)") == "KRISTINA WONG #FoodBankInfluencer"
    assert _base("WHEN YURI MET MALCOLM at Westwood Branch Library") == "WHEN YURI MET MALCOLM"
    assert _base("Night at the Museum") == "Night at the Museum"


def test_collapse_runs_folds_variants_and_leaves_others():
    evs = [_ev("Passing Strange", "2026-11-07T19:30:00-08:00"),
           _ev("Passing Strange", "2026-11-08T19:30:00-08:00"),
           _ev("Passing Strange WINE WEDNESDAY", "2026-11-11T19:30:00-08:00"),
           _ev("Passing Strange CLOSING", "2026-11-29T19:00:00-08:00"),
           _ev("One Night Only", "2026-11-20T20:00:00-08:00"),
           _ev("Passing Strange", "2026-11-09T19:30:00-08:00", vid="museum")]
    out = collapse_runs(evs, {"theater"})
    runs = [e for e in out if e.get("_run")]
    assert len(runs) == 1
    r = runs[0]
    assert r["title"] == "Passing Strange" and r["start"] == "2026-11-07" and r["end"] == "2026-11-29"
    assert r["run_count"] == 4
    assert any(e["title"] == "One Night Only" for e in out)
    assert any(e["venue_id"] == "museum" for e in out)       # non-performing venue untouched


def test_weekly_series_is_not_a_run():
    evs = [_ev("Dance Practice with Adie", f"2026-11-{d:02d}T18:00:00-08:00") for d in (5, 12, 19, 26)]
    out = collapse_runs(evs, {"theater"})
    assert not any(e.get("_run") for e in out)      # left for the recurring filter to hide


def test_times_and_dashes_are_not_ranges():
    assert gl.parse_dates("Saturday, December 6, 2026 - 7pm", TODAY) == (date(2026, 12, 6), None, "19:00")
    assert gl.parse_dates("Dec 12 - 8:00 PM", TODAY) == (date(2026, 12, 12), None, "20:00")
    assert gl.parse_dates("Dec 6 2026 | 7-9pm", TODAY)[2] == "19:00"
    assert gl.parse_dates("Dec 6, 11-1pm", TODAY)[2] == "11:00"


def test_annual_production_is_not_one_run():
    evs = [_ev("The Nutcracker", f"2025-12-{d:02d}T19:00:00-08:00") for d in (5, 6, 7)] + \
          [_ev("The Nutcracker", f"2026-12-{d:02d}T19:00:00-08:00") for d in (12, 13, 14)]
    runs = [e for e in collapse_runs(evs, {"theater"}) if e.get("_run")]
    assert sorted((r["start"], r["end"]) for r in runs) == [("2025-12-05", "2025-12-07"), ("2026-12-12", "2026-12-14")]


def test_dry_run_never_calls_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ART_IN_LA_DRY_RUN", "1")
    assert llm.enabled() is False
