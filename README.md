# Art in LA

A comprehensive, community-maintained map and calendar of visual art venues and events across Los Angeles County — museums, galleries, community spaces, and alternative venues.

- **~150 venues** across LA County with address, map coordinates, description, and social links
- **Interactive map** with color-coded markers by venue type, plus a toggle to show only venues with upcoming public events
- **Filterable listings** of events and venues (by type, region, date)
- **Automatic archive** of past events
- **Daily scraper cron** via GitHub Actions — each venue has its own scraper module
- **Zero infrastructure cost**: static site on GitHub Pages, scrapers on GitHub Actions, map tiles via OpenStreetMap / CARTO — no API keys required

## Quick start (deploying your own copy)

### 1. Fork & rename

1. Fork this repo.
2. Rename the fork to whatever you want — e.g. `art-in-la` or `la-art-calendar`. The site URL will be `https://<your-github-username>.github.io/<repo-name>/`.
3. (Done — set to `birdofnofeather`.) If you fork and rename later, update `src/App.jsx` footer link and `scrapers/utils/http.py` User-Agent.

### 2. Enable GitHub Pages

1. Go to **Settings → Pages**.
2. Under **Source**, choose **GitHub Actions**.
3. (That's it — the `deploy.yml` workflow handles the rest.)

### 3. Enable the daily scrape

1. Go to **Settings → Actions → General**.
2. Under **Workflow permissions**, choose **Read and write permissions** and save. (This lets the scraper commit updated JSON.)
3. Push to `main` — the first deploy workflow will run. You can also run scrapers manually from the **Actions** tab → **Daily scrape** → **Run workflow**.

### 4. (Optional) Customize

- **Change the cron time**: edit the `cron` expression in `.github/workflows/daily-scrape.yml`. It's UTC.
- **Change the map center or zoom**: `src/components/VenueMap.jsx` has `CENTER` and `ZOOM` constants at the top.
- **Change colors or fonts**: `tailwind.config.js`.

## Local development

You need Node 20+ and Python 3.12+.

```bash
# Frontend (Vite dev server)
npm install
npm run dev                # http://localhost:5173

# Run scrapers (updates public/data/events.json and archive.json)
pip install -r scrapers/requirements.txt
python -m scrapers.run_all                    # run all scrapers
python -m scrapers.run_all --only lacma       # just one venue
python -m scrapers.run_all --dry-run          # print a summary, don't write files
```

## Project layout

```
art-in-la/
├── public/data/            # Site data — read at runtime by the site
│   ├── venues.json         # Hand-curated venue database
│   ├── events.json         # Scraped upcoming events (written by CI)
│   ├── archive.json        # Past events (rolled over by CI)
│   └── SCHEMA.md           # Schema documentation
├── src/                    # React + Vite frontend
│   ├── App.jsx             # Tab-based main view
│   ├── components/         # VenueMap, FilterBar, EventList, VenueList, Header
│   └── lib/                # constants, filters, data loader
├── scrapers/               # Python scrapers
│   ├── base.py             # BaseScraper with 4 default strategies
│   ├── registry.py         # List of active scrapers
│   ├── run_all.py          # Main entry point — dedupe, archive, write JSON
│   ├── venues/             # One module per venue
│   └── utils/              # HTTP, dedup, archive, event-id, date parsing
└── .github/workflows/
    ├── deploy.yml          # Build + deploy to GitHub Pages
    └── daily-scrape.yml    # Run scrapers + commit data (cron)
```

## How the scrapers work

Each venue has a small module under `scrapers/venues/` that subclasses `BaseScraper`. In most cases the subclass only needs to set class attributes — the base class tries four strategies in order:

1. **JSON-LD schema.org/Event** embedded in the events page — the most common modern pattern.
2. **iCal feed** (set `ical_url`) — most WordPress-based sites using The Events Calendar expose one at `/events/?ical=1`.
3. **RSS / Atom feed** (set `feed_url`).
4. **Custom HTML parsing** — override `custom_parse(html, base_url)` in the subclass.

Scraped events are then deduplicated by a stable `event_id` (derived from `venue_id` + date + normalized title), so if the same event surfaces through multiple strategies or multiple sources for the same venue, only the richest record is kept.

### Adding a venue scraper

1. Make sure the venue exists in `public/data/venues.json`. If not, add it.
2. Create `scrapers/venues/<id>.py`:

   ```python
   from ..base import BaseScraper

   class Scraper(BaseScraper):
       venue_id = "new_venue"
       events_url = "https://example.com/events"
       source_label = "example.com"
       # Optional:
       # ical_url = "https://example.com/events/?ical=1"
       # feed_url = "https://example.com/events/feed"
   ```

3. Append the class to `SCRAPERS` in `scrapers/registry.py`.
4. Test locally: `python -m scrapers.run_all --only new_venue`.
5. Open a PR.

### What about Instagram / TikTok?

Social handles are stored in `venues.json` and rendered as links in the UI, but we don't automatically scrape posts — Meta and TikTok actively block third-party scrapers and neither has an API that suits this use case for public venues. If a venue only publishes events on Instagram, the most robust path is:

- Check if their website also has an events page (usually does).
- Check for a Linktree / Beacons / Bio.fm link that points to an events calendar.
- Fall back to manually listing a few events by opening a PR that appends them to `public/data/events.json` (respect the schema in `SCHEMA.md`).

## Contributing

See `CONTRIBUTING.md` for how to add a venue, fix data, or improve a scraper.

## License

MIT. Data contributed via PRs is likewise MIT; if you add an event record derived from a source with a more restrictive license, please note it in the PR.
