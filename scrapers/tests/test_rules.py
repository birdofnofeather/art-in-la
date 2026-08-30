"""The rules file must always agree with the examples written inside it.

This is the test that protects deliberate curation decisions. If someone — you,
or an automated repair — weakens the recurring filter to make a venue's event
count look healthier, Getty's garden tour reappears and this fails.
"""
from scrapers.check_rules import check
from scrapers.utils.rules import load


def test_every_example_in_rules_yaml_behaves_as_written():
    assert check() == 0, "scrapers/rules.yaml disagrees with its own examples"


def test_rules_file_is_structurally_sound():
    rules = load()
    assert rules.event_types, "no event types defined"
    assert "other" in rules.type_ids, "the 'other' fallback type is required"
    assert rules.recurring_drop, "no standing-programme patterns defined"
    assert rules.forbid_in_text, "no text-quality rules defined"


def test_cadence_settings_are_sane():
    """A misconfigured cadence would silently hide or reveal hundreds of events."""
    rules = load()
    assert rules.cadence_min_occurrences >= 2
    assert rules.cadence_min_gap_days >= 2, (
        "a gap floor below 2 days would hide theatre runs and festival days, "
        "which are real events"
    )
    assert rules.cadence_min_gap_days < rules.cadence_max_gap_days
    assert rules.cadence_absolute_threshold >= rules.cadence_min_occurrences
