# Contributing

Thanks for helping keep this accurate. Three kinds of contributions are most valuable:

## 1. Fix or add a venue

`public/data/venues.json` is the source of truth for the venue database. Edit it directly. Fields:

| Field         | Required | Notes |
|---------------|----------|-------|
| `id`          | yes      | Stable slug, lowercase, snake_case. Never change after first merge. |
| `name`        | yes      | Full legal or public-facing name. |
| `short_name`  | no       | Shown on map tooltips. |
| `type`        | yes      | `museum` / `gallery` / `community` / `alternative` / `academic`. |
| `description` | yes      | One sentence, ~20 words. |
| `website`     | yes      | Landing page. |
| `events_url`  | no       | Where upcoming events live. Used by scrapers. |
| `address`     | yes      | Postal address as a single string. |
| `lat`, `lng`  | yes      | Decimal degrees. If you're unsure, Google the venue and right-click → copy coordinates. |
| `region`      | yes      | One of: `westside`, `central`, `eastside`, `northeast`, `valley`, `south`, `southbay`, `pasadena`, `longbeach`, `antelope`. |
| `neighborhood`| yes      | Casually correct neighborhood name. |
| `socials`     | no       | Full URLs keyed by platform. See existing entries. |

When you add a venue, keep the JSON sorted however you like — the list is not order-sensitive. Please also write a scraper for it (see below) or open an issue asking someone else to.

## 2. Add or improve a scraper

Most venues can be scraped with only URL configuration. Full instructions are in `README.md` under "Adding a venue scraper". If a venue's HTML is irregular enough that the base strategies don't work, override `custom_parse()` with site-specific BeautifulSoup code. Aim for:

- Return-types: yield `Event` dataclass instances from `scrapers.base`.
- Robustness: a failing scraper should return `[]`, not raise. The runner catches exceptions per scraper, but fewer tracebacks means nicer logs.
- Rate-limits: the shared `scrapers.utils.http.get` has retries + backoff. Don't hammer.

## 3. Add events manually

Some venues only publish events on Instagram or via an email newsletter. Those can be added to `public/data/events.json` by hand. The schema is in `public/data/SCHEMA.md`. Generate the `id` with:

```python
from scrapers.utils.event_id import event_id
print(event_id("venue_id_here", "2026-05-01T19:00:00-07:00", "Opening reception: Some Title"))
```

When a scraper for the same venue later surfaces the same event, the deterministic ID will dedupe them automatically.

## Code style

- Python: keep it readable; add a docstring to every new module.
- JavaScript/JSX: follow the patterns in existing components (plain React, no extra state libraries, Tailwind utility classes).
- Data: all event times are stored with an explicit timezone offset. LA venues use `-07:00` (PDT) or `-08:00` (PST). Helpers in `scrapers/utils/dateparse.py` do the coercion.

## PR checklist

- [ ] `npm run build` passes locally.
- [ ] `python -m scrapers.run_all --dry-run` prints the expected number of events for changed venues.
- [ ] JSON files are valid (`python -m json.tool public/data/*.json`).
