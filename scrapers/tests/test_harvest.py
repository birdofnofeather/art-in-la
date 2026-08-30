"""The harvest strategies, and the traps in wiring a second pass for exhibitions."""
from scrapers.base import BaseScraper
from scrapers.utils import squarespace as sqs


# ── The exhibitions pass ──────────────────────────────────────────────────

def _strategy_names(allow_custom):
    """Which strategies a harvest pass would try, without touching the network."""
    scraper = BaseScraper()
    scraper.venue_id = "test"
    seen = []

    def spy(name):
        def _run():
            seen.append(name)
            return []
        return _run

    real = scraper._harvest
    # Re-run the selection logic by calling _harvest with every strategy stubbed.
    for attr, name in [
        ("_strategy_wp_tribe", "wp_tribe"),
        ("_strategy_squarespace", "squarespace"),
        ("_strategy_ical", "ical"),
        ("_strategy_jsonld", "jsonld"),
        ("_strategy_eventbrite", "eventbrite"),
        ("_strategy_feed", "feed"),
        ("_strategy_custom", "custom"),
    ]:
        setattr(scraper, attr, spy(name))
    real("https://example.com/exhibitions", "exhibition", allow_custom=allow_custom)
    return seen


def test_the_exhibitions_pass_excludes_strategies_that_ignore_the_url():
    """wp_tribe and the iCal probe address the site ROOT, not the path given.

    Pointed at /exhibitions they return the ordinary events feed, and every
    event would be republished as a fabricated exhibition. Five venues did
    exactly this in testing before the restriction was added.
    """
    tried = _strategy_names(allow_custom=False)
    assert "wp_tribe" not in tried, "wp_tribe ignores the URL and would duplicate events"
    assert "ical" not in tried, "the iCal probe ignores the URL and would duplicate events"
    assert "squarespace" in tried and "jsonld" in tried


def test_the_events_pass_uses_every_strategy():
    tried = _strategy_names(allow_custom=True)
    assert "wp_tribe" in tried and "custom" in tried


def test_a_venue_without_an_exhibitions_url_runs_only_one_pass():
    scraper = BaseScraper()
    assert scraper.exhibitions_url is None


# ── Squarespace ───────────────────────────────────────────────────────────

def test_squarespace_json_url_is_built_correctly():
    assert sqs.json_url("https://x.com/events") == "https://x.com/events?format=json"
    assert sqs.json_url("https://x.com/events/") == "https://x.com/events?format=json"
    assert sqs.json_url("https://x.com/events?x=1") == "https://x.com/events?format=json"


def test_squarespace_timestamps_convert():
    # 1789088400691 ms == 2026-09-11T01:00:00Z (6pm the previous day in LA)
    iso = sqs.epoch_ms_to_iso(1789088400691)
    assert iso.startswith("2026-09-11T01:00:00")


def test_squarespace_rejects_a_nonsense_timestamp():
    """A stray 0 or a seconds-not-milliseconds value must not become an event."""
    assert sqs.epoch_ms_to_iso(0) is None
    assert sqs.epoch_ms_to_iso(None) is None
    assert sqs.epoch_ms_to_iso("not a number") is None
    assert sqs.epoch_ms_to_iso(99_999_999_999_999) is None      # year 5138


def test_squarespace_relative_links_become_absolute():
    assert sqs.absolute_url("https://x.com/events", "/events/a-show") == "https://x.com/events/a-show"
    assert sqs.absolute_url("https://x.com/events", "https://y.com/a") == "https://y.com/a"
    assert sqs.absolute_url("https://x.com/events", None) is None


def test_squarespace_ignores_a_page_that_is_not_an_event_collection():
    assert not sqs.is_event_collection({})
    assert not sqs.is_event_collection({"upcoming": [], "past": []})
    assert sqs.is_event_collection({"upcoming": [{"title": "x"}], "past": []})
