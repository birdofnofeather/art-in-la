# Data Schema

The site reads three JSON files from `/data/`:

- `venues.json` — all organizations (museums, galleries, community, alternative, academic)
- `events.json` — upcoming and currently-on events
- `archive.json` — past events (automatically moved here by the archiver)

## Venue

```jsonc
{
  "id": "lacma",                    // Stable unique slug. Used as the key for scraper dedup and event linking.
  "name": "Los Angeles County Museum of Art",
  "short_name": "LACMA",            // Optional. Shown on map marker tooltips and list cards.
  "type": "museum",                 // museum | gallery | community | alternative | academic
  "description": "One line.",
  "website": "https://www.lacma.org",
  "events_url": "https://www.lacma.org/events",  // Optional, used by scrapers
  "address": "5905 Wilshire Blvd, Los Angeles, CA 90036",
  "lat": 34.0638,                   // Required for map
  "lng": -118.3594,                 // Required for map
  "region": "central",              // westside | central | eastside | northeast | valley | south | southbay | pasadena | longbeach | antelope
  "neighborhood": "Miracle Mile",
  "socials": {
    "instagram": "https://...",     // All fields optional; include full URL, not handle
    "twitter": null,
    "facebook": null,
    "bluesky": null,
    "threads": null,
    "tiktok": null,
    "youtube": null
  }
}
```

## Event

```jsonc
{
  "id": "lacma-2026-05-01-opening-reception",   // Deterministic hash of venue_id + start + title, used for dedup
  "venue_id": "lacma",                          // FK to venue
  "title": "Opening Reception: Mary Weatherford",
  "description": "One-paragraph description.",
  "event_type": "opening",                      // opening | closing | workshop | lecture | performance | screening | tour | fair | other
                                                //
                                                // NOTE: `exhibition` is no longer captured. The scraper drops any event
                                                // with a duration > 36h. If the start has a specific time-of-day, it
                                                // synthesizes an "Opening: <title>" event from it instead.
  "start": "2026-05-01T19:00:00-07:00",         // ISO 8601 with tz
  "end": "2026-05-01T21:00:00-07:00",           // Optional; inclusive end
  "all_day": false,
  "url": "https://www.lacma.org/events/...",    // Detail page for this event
  "image": "https://...",                       // Optional hero image
  "artists": ["Mary Weatherford"],              // Optional list of featured artists/presenters
  "location_override": null,                    // If not at the venue's main address, free text
  "source": "lacma.org",                        // Which source produced the record; used for dedup
  "scraped_at": "2026-04-24T07:15:00Z"          // ISO 8601 UTC timestamp
}
```

### Map view: which venues are shown

The Map view always filters to venues with at least one upcoming one-off event (opening, closing, workshop, lecture, performance, screening, tour, fair, or other). Exhibitions are not captured at all (see note above), so this filter is effectively "any upcoming event."

The Venues tab shows the full curated database regardless of upcoming events.
