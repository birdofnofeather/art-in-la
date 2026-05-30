# Archived gallery scrapers

These commercial gallery scrapers were retired on 2026-05-30 when the project
narrowed its scope to **museums and non-commercial art institutions in LA County**.

They are kept here (not deleted) for reference and easy restoration. They are
**not** imported by `scrapers/registry.py` and therefore do not run in the daily
cron. The corresponding venues were also removed from `public/data/venues.json`
and their events purged from `events.json` / `archive.json`.

To bring one back: move the module up to `scrapers/venues/`, re-add its import and
`SCRAPERS` entry in `registry.py`, and restore the venue record in `venues.json`.
