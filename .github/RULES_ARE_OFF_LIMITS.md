# Files an automated repair must never edit

This project is designed to repair its own scrapers without a human in the loop.
That is safe only while the automation cannot change what the site is *for*.

## Off limits to any automated change

| File | Why |
|---|---|
| `scrapers/rules.yaml` | Every curation decision — event types, which recurring programmes are hidden, what counts as an exhibition, what is clean enough to publish. |
| `public/data/venues.json` | The hand-curated venue list. Adding or removing a venue is an editorial decision. |
| `scrapers/tests/**` | The tests are the check on the automation. Automation that can edit its own tests is not checked by them. |
| `.github/workflows/**` | The automation must not be able to widen its own permissions or disable its own safety gates. |
| This file | For the obvious reason. |

## Why this matters

The single most tempting way to "fix" a venue whose event count has dropped is
to weaken the recurring filter. It works, in the sense that the number goes up
and the test goes green. It also silently undoes deliberate decisions: Getty's
*Art, Architecture, and Garden Tour*, LACMA's gallery tours, Huntington's
standing educator programmes, and Pieter's weekly dance classes are excluded on
purpose, not by accident.

An automated repair rewarded for "more events" would remove all of them and
report success.

## How it is enforced

Three layers, because a rule that exists only in prose is not enforced at all:

1. **`scrapers/check_rules.py`** runs every rule in `rules.yaml` against the
   examples stored beside it. The `reject:` examples are the important half —
   they name real events that must stay visible. Weakening a pattern breaks
   them immediately.
2. **The test suite** (`scrapers/tests/test_rules.py`) runs that check on every
   push, so a change cannot be merged without it passing.
3. **The repair job's own instructions** list these paths as forbidden, and its
   diff is rejected if it touches one.

## If a rule genuinely needs to change

Edit `rules.yaml` yourself, update the examples in the same commit to describe
the new intended behaviour, and run:

```bash
python -m scrapers.check_rules        # do the examples still agree?
python -m scrapers.reclassify --dry-run   # what would change across all data?
```

The dry run tells you exactly how many events change type and which series
appear or disappear — before anything is published.
