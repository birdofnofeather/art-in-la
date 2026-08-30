"""Text repair and the quality gate.

The bug behind these tests: six Getty events reached the live site reading
"Instante/revelaciÃ³n" and "espaÃ±ol". Counts were normal, dates were fine, and
nothing in the pipeline was looking at whether the text was readable.
"""
from scrapers.utils.text import fix_mojibake, looks_mojibaked, normalise, title_key
from datetime import date, timedelta

from scrapers.utils.validate import quality_report, validate

# Far enough ahead to be 'upcoming', near enough to stay inside the
# plausible-future bound in rules.yaml (which is itself a real rule).
SOON = (date.today() + timedelta(days=90)).isoformat()
LONG_AGO = (date.today() - timedelta(days=400)).isoformat()


# ── Repair ────────────────────────────────────────────────────────────────

def test_the_getty_corruption_is_repaired():
    assert normalise("Instante/revelaciÃ³n") == "Instante/revelación"
    assert normalise("espaÃ±ol") == "español"


def test_a_mangled_curly_apostrophe_is_repaired():
    assert normalise("Stendahlâs World") == "Stendahl’s World"


def test_correct_text_is_left_alone():
    """The repair must never damage text that was fine to begin with."""
    for good in [
        "café",
        "Instante/revelación",
        "Perfectly fine title — with an em dash",
        "Tātau Bookmark Workshop",
        "Plática y Prueba",
    ]:
        assert normalise(good) == good, f"{good!r} was altered"


def test_unrepairable_corruption_is_not_guessed_at():
    """'Ãdouard' lost the byte that would identify it as 'Édouard'.

    Inventing a replacement would be worse than leaving it: report, don't guess.
    """
    assert normalise("Ãdouard Manet") == "Ãdouard Manet"


def test_detection_does_not_fire_on_ordinary_text():
    assert not looks_mojibaked("A perfectly normal event title")
    assert not looks_mojibaked("")
    assert looks_mojibaked("revelaciÃ³n")


def test_fix_is_stable_when_applied_twice():
    once = fix_mojibake("Instante/revelaciÃ³n")
    assert fix_mojibake(once) == once


# ── Title comparison ──────────────────────────────────────────────────────

def test_title_key_ignores_punctuation_and_accents():
    """So a series is recognised even when the venue is inconsistent."""
    a = title_key("Queerchata: Intro to Salsa ")
    assert a == title_key("Queerchata — Intro to Salsa")
    assert a == title_key("queerchata intro to salsa")


# ── The quality gate ──────────────────────────────────────────────────────

def _ev(**kw):
    base = {
        "id": "x", "venue_id": "test", "title": "A Real Event",
        "event_type": "lecture", "start": SOON, "description": "",
    }
    base.update(kw)
    return base


def test_leftover_html_blocks_publication():
    blocking, _ = quality_report(_ev(title="An Event <br> With Markup"))
    assert blocking, "raw HTML in a title must stop it being published"


def test_missing_required_field_blocks_publication():
    blocking, _ = quality_report(_ev(venue_id=""))
    assert any("venue_id" in b for b in blocking)


def test_unreconstructable_accent_is_reported_not_dropped():
    """A real event with one bad character is still worth showing."""
    blocking, reportable = quality_report(_ev(title="Ãdouard Manet and the Salon"))
    assert not blocking, "we must not lose a real event over one character"
    assert reportable, "...but it must still be reported"


def test_a_clean_event_has_no_complaints():
    blocking, reportable = quality_report(_ev())
    assert not blocking and not reportable


def test_validate_repairs_corruption_rather_than_dropping_it():
    kept, dropped = validate([_ev(title="Instante/revelaciÃ³n", start=SOON)])
    assert len(kept) == 1, "a repairable title must not cost us the event"
    assert kept[0]["title"] == "Instante/revelación"
    assert not dropped


def test_validate_drops_an_event_with_no_date():
    kept, dropped = validate([_ev(start=None)])
    assert kept == [] and len(dropped) == 1


def test_validate_keeps_an_undated_exhibition_that_has_an_end_date():
    kept, _ = validate([_ev(event_type="exhibition", start=None, end=SOON)])
    assert len(kept) == 1
