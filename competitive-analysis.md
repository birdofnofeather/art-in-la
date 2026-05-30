# Art in LA — Competitive Analysis, Gap Analysis & Roadmap
*Prepared May 2026*

---

## 1. Competitor overview

### Artforum Artguide — artguide.artforum.com
**Audience:** Collectors, critics, art world professionals, culturally sophisticated visitors. Global reach.
**What it does:** The most authoritative English-language guide to contemporary art exhibitions worldwide. For LA specifically it covers commercial galleries, museums, auction houses, and major non-profit institutions. Features include neighborhood browsing, "myguide" personal planner, a mobile app, and Critics' Picks editorial. Venues pay a membership fee to be listed. Crawl-delay on their robots.txt is 30 seconds; main listing paths are not disallowed.
**Strengths:** Authority, depth, editorial quality, global recognition, mobile app, personal planning tools.
**Weaknesses:** LA coverage skews heavily commercial/blue-chip. No community arts centers, no alternative spaces, no academic galleries. Listings depend on gallery membership — not scraped. No archive. US-centric editorial can be NYC-biased.

---

### GalleryPlatform.LA (GP.LA) — galleryplatform.la
**Audience:** LA-based art collectors, gallery hoppers, local art community, tourists.
**What it does:** A project of the Gallery Association of Los Angeles (GALA). Approximately 90+ member galleries. Provides events, exhibitions, neighborhood walking guides, editorial video content (artist studio visits), and a PWA mobile app. Data is fully member-submitted — not scraped.
**Strengths:** Genuinely local, beautiful design, excellent neighborhood guides, editorial video series, PWA, active social presence.
**Weaknesses:** Members-only coverage (if a gallery didn't join GALA, it's invisible). No community centers, no academic galleries, no alt spaces. No archive. No search bar. Their ToS explicitly prohibits harvesting/scraping (Section 3(a)(vi)).

---

### Ocula — ocula.com
**Audience:** International collectors, dealers, art market professionals.
**What it does:** Global art market platform. Artist profiles, exhibition listings, gallery directory, editorial magazine, auction results. Membership model for galleries. LA listings present but LA is one of 50+ cities.
**Strengths:** Artist database, market intelligence, exhibition imagery, global collector network, editorial.
**Weaknesses:** No LA focus. No community/alternative venues. No map. Gated features. Commercial-only.

---

### GalleriesNow — galleriesnow.net
**Audience:** International gallery visitors, collectors, art lovers.
**What it does:** Daily-updated exhibition listings for leading commercial galleries in 10+ major cities. Features include map view, "open today" filter, exhibition images and descriptions, artwork count, hours. Membership tiers for unlimited saves and full archive access.
**Strengths:** Updated daily, "open today" filter, clean UX, global reach, exhibition images, hours displayed.
**Weaknesses:** Only covers "leading galleries" — entirely commercial. No LA-specific depth. No community/alt/academic venues. Archive behind paywall.

---

### Artweek — artweek.com
**Audience:** Artists, galleries, collectors, international art community.
**What it does:** Multi-city events and exhibition calendar. Venues and users can self-submit listings. Covers exhibitions, talks, openings, film, photography. LA is one of several cities.
**Strengths:** Free self-submission, broad event types, global reach, opportunities listings (calls for artists).
**Weaknesses:** No map. No archive. Sparse design. Not LA-specific. Dependent on self-reporting — coverage is patchy.

---

### Artnet Events — artnet.com/events
**Audience:** Art market professionals, collectors, press.
**What it does:** Events calendar alongside Artnet's main art market tools (price database, news, auctions). Primarily driven by major gallery and museum submissions.
**Strengths:** Art market authority, price database (huge differentiator), global reach, auction records.
**Weaknesses:** Events listing is a small secondary feature. No LA focus. No map. No community venues.

---

### Art-Collecting.com
**Audience:** Casual collectors, art tourists, newcomers to the art world.
**What it does:** Static gallery directory and fair guide organized by US city. Low-tech, text-heavy, manually maintained.
**Strengths:** Easy to navigate for newcomers, art fair dates.
**Weaknesses:** Largely static/unmaintained. No events calendar, no map, no dynamic data.

---

## 2. Audience analysis

| Segment | Who they are | Underserved by competition? |
|---|---|---|
| **Art world professionals** | Gallerists, curators, critics, dealers | Well-served by Artforum, Ocula |
| **Collectors (high-end)** | Blue-chip buyers, fair attendees | Well-served by Artnet, Ocula |
| **Gallery hoppers** | LA residents exploring the scene | Partially served by GP.LA (member-only), Artforum |
| **Community arts audience** | Residents engaging with Self Help Graphics, Avenue 50, Human Resources, SPARC | **Significantly underserved** |
| **Students / academics** | Art school students, faculty, SCI-Arc, CalArts | **Significantly underserved** |
| **Alt space followers** | Attendees of experimental, literary, and DIY spaces | **Significantly underserved** |
| **Tourists / casual visitors** | First-timers wanting a weekend itinerary | Partially served (no "what's on this weekend" view) |
| **Researchers** | People studying LA's art history/ecosystem | Partially served (our archive is unique) |

Our real audience opportunity is the middle tiers: LA residents who care about the full ecosystem — from the Broad to Self Help Graphics — not just the commercial gallery circuit.

---

## 3. What Art in LA offers that no one else does

These are genuine differentiators — not just "also has":

1. **Community + alt + academic venue coverage.** No other platform systematically covers Self Help Graphics, Human Resources LA, SPARC, Angels Gate, Avenue 50, Corita Art Center, CalArts, SCI-Arc, USC Fisher, PVAC, Vincent Price Art Museum, Brand Library, and ~30 more community/nonprofit/university spaces. This is the site's clearest identity and biggest moat.

2. **Auto-scraped, not self-reported.** 108 of 159 venues have active scrapers running daily via GitHub Actions. Data is pulled directly from venue websites, not dependent on venues paying a fee or remembering to update a listing. This means less lag on newly announced events and no gaps from venues that never joined a commercial platform.

3. **Open source / forkable.** MIT license. Any city could fork this for their own art scene. This has network and trust value that commercial platforms can't match.

4. **Event archive.** The growing archive of past events is unique among LA-focused platforms. Useful for researchers, for understanding which venues are active, and for future machine-learning applications (trend identification, etc.).

5. **Fully free, zero gating.** No account, no paywall, no premium tier. Every feature is equally accessible to a 17-year-old student in Watts and a collector in Bel-Air.

6. **Map-first cross-linking.** The "show on map" / "see events" cross-navigation between the calendar and map is more fluid than any competitor.

---

## 4. What we're duplicating that others already do better

Be honest about where we're redundant:

- **Blue-chip commercial gallery listings** (Gagosian, Hauser & Wirth, David Kordansky, Blum, Sprüth Magers, etc.): Artforum, GP.LA, and GalleriesNow all cover these better — with images, editorial context, and venue-submitted accuracy. Our scrapers for these galleries add marginal value to a user who already checks those platforms.
- **Museum event calendars** (LACMA, Hammer, Broad, Getty, MOCA): These museums' own websites are authoritative. Artforum also covers them. We should retain these for completeness and map presence, but they're not our differentiator.
- **Basic exhibition listings without images or descriptions**: Every competitor has this. Without images, our listings for commercial galleries are strictly inferior UX.

**Conclusion on gallery scrapers:** Don't pull them entirely — the calendar completeness and map presence matter. But stop treating commercial gallery scraper coverage as a feature that differentiates us. The scraper effort is best spent on the venues no one else covers. When a Gagosian scraper breaks, it's low priority to fix. When a Self Help Graphics scraper breaks, fix it fast.

---

## 5. Legal guidance: scraping Artforum Artguide

**Can you scrape Artforum's listings for your site, given you're in California?**

The short answer is: **technically lower-risk than you'd think for pure factual data, but not recommended for practical reasons.**

**The legal landscape:**

- **Artforum's robots.txt** (verified May 2026) sets a 30-second crawl delay but only disallows `/admin`, `/search`, `/newsletter`, `/ads`, `/cart`, `/image`, `/app.php`, and `/dev`. The listing pages (`/artguide/place/los-angeles`) are **not disallowed**.
- **Factual data is not copyrightable.** Under *Feist Publications v. Rural Telephone* (US Supreme Court, 1991), a compilation of facts — venue names, addresses, exhibition titles, artist names, dates — is not protected by copyright because it lacks the required "creativity." You can legally republish those facts.
- **The hiQ v. LinkedIn ruling (9th Circuit, 2022):** Scraping publicly accessible data from sites that don't require login does not violate the Computer Fraud and Abuse Act (CFAA). As a California resident, you're in the 9th Circuit.
- **Artforum's Terms & Conditions** (visible at the bottom of the artguide help page) say "All rights reserved" and include standard prohibitions on unauthorized use. However, a ToS violation is a *breach of contract* claim, not a CFAA or copyright claim — and requires Artforum to prove damages and that you agreed to their ToS. For a small community project scraping factual listing data, the real-world risk is very low.
- **California CPRA/CCPA** applies to *personal data*. Gallery exhibition listings are not personal data.

**What you should and shouldn't do:**

| Scraping target | Risk level | Recommendation |
|---|---|---|
| Venue name, address, phone, website | Very low | OK if needed, but you already have this |
| Exhibition title + artist name + dates | Low | Factual, not copyrightable |
| Artforum's editorial descriptions of exhibitions | **High** | Do not copy — this is original creative writing, clearly copyrightable |
| Images from Artforum listings | **High** | Do not use — these are licensed photographs |

**Practical recommendation: don't scrape Artforum.** Not because it's clearly illegal, but because it's not worth it. Their *factual* data (names, dates) is already available directly on the venues' own websites, which is where your scrapers already go. There's no need to route through Artforum. And their *non-factual* data (descriptions, images) you can't use anyway.

**What you CAN do instead:** Link OUT to Artforum listings. A "View on Artforum" link on each venue page costs nothing and adds real value. Artforum is useful to your users; directing them there is a feature, not a defeat.

---

## 6. Gap analysis: what's missing

Grouped by impact vs. implementation cost:

### High-impact gaps

| Gap | Why it matters | Notes |
|---|---|---|
| No search bar | Every competitor has one. Users can't find a specific venue or artist by name. | Simple client-side fuzzy search over `venues.json` + `events.json`. No backend needed. |
| No venue hours / "open today" | GalleriesNow gets this right and it's genuinely useful. Without hours, the map is less actionable for a Saturday visit. | Requires adding `hours` field to `venues.json`. Manual data entry but one-time per venue. |
| No images in listings | Every competitor shows artwork images. Text-only listings are a significant UX disadvantage — users scroll past them. | Could be added as an optional `image_url` field from scrapers (venues' own OG images, no copyright issue). |
| No venue submission path | Venues and community members can't easily add themselves. GitHub PRs are too technical for most people. | A simple Google Form → GitHub issue (or direct JSON PR template) would work without infrastructure cost. |
| No newsletter | Every competitor has one. A weekly "what's on" digest is the highest-retention touchpoint for this audience type. | Buttondown.email is free up to 100 subscribers, $9/mo after. Could be populated by a GitHub Action that renders this week's events. |
| No neighborhood guide pages | GP.LA's neighborhood guides are excellent and well-used. This is high-value content for both SEO and tourist use cases. | Static markdown pages — zero scraping required, manually written once. |

### Medium-impact gaps

| Gap | Why it matters | Notes |
|---|---|---|
| No "this weekend" quick view | The most common use case for a casual visitor. | Date filter shortcut, already mostly possible — just needs a prominent UI button. |
| No quick stats / data page | "How many events happened in 2025?" "Which neighborhood has the most openings?" | The archive already contains this data. A simple static stats page built during CI would be compelling and shareable. |
| No art fair calendar | LA has Frieze, Felix, NADA, The Other Art Fair, etc. These are major cultural moments. | Could be a static JSON file + simple listing page — no scrapers needed. |
| No "recently closed" view | What did I miss? Useful for the archive. | Already have the data — just a UI addition. |

### Lower-priority / backlog gaps

- User saves/favorites (localStorage, no auth required)
- Mobile PWA / installable
- Artist index from scraped event titles
- Geolocation "near me" filter
- Dark mode
- Accessibility audit (WCAG)
- Venue-level stats pages ("15 exhibitions this year")

---

## 7. Scraper strategy given limited maintenance capacity

Given that you have limited capacity to troubleshoot scrapers in the future, here's a triage framework:

**Tier 1 — Protect at all costs** (high unique value, not covered elsewhere):
Self Help Graphics, Human Resources LA, Angels Gate, Avenue 50, Corita Art Center, LACE, SPARC, Beyond Baroque, Institute of Contemporary Art LA, Commonwealth & Council, Vincent Price Art Museum, Brand Library, Armory Center for the Arts, CalArts, SCI-Arc, USC Fisher, Fowler Museum, PVAC, Craft Contemporary, Pieter, Charlie James, Joan, Art Practice, 18th Street Arts Center, Wende Museum

**Tier 2 — Maintain but deprioritize fixes** (museum/institution events also on their own prominent websites):
LACMA, Hammer, The Broad, MOCA, Getty, Huntington, JANM, Skirball, Autry, CAAM, LA Plaza, Fowler

**Tier 3 — Low priority to fix when broken** (blue-chip commercial galleries well-covered by GP.LA, Artforum, GalleriesNow):
Gagosian, Hauser & Wirth, David Kordansky, Blum, Sprüth Magers, Zwirner, Pace, Regen Projects, Lisson, Perrotin, Marian Goodman

**Reliability improvements that reduce maintenance:**
- Add scraper health dashboard to the GitHub Actions summary — one glance shows which scrapers are returning zero events.
- For Tier 3 galleries: switch from custom scrapers to a simple iCal/RSS check. If the feed breaks, fail silently rather than crashing the run.
- Add a `last_scraped_successfully` date to each venue's metadata so the UI can show a warning when data is stale.

---

## 8. MVP recommendations (ship these first)

These are the features that bring *new, real value* to users and the community, are implementable without new infrastructure, and don't require ongoing maintenance overhead.

### MVP 1: Search bar
**Impact:** High. It's the single biggest usability gap vs. every competitor.
**Implementation:** Client-side fuzzy search (Fuse.js, ~4KB gzipped) over venues.json + events.json. No backend. Works offline. One PR.
**Tools needed:** `npm install fuse.js`, add a search input to the Header component, wire to a results dropdown.
**Effort:** ~1 day.

### MVP 2: Venue hours + "open today" filter
**Impact:** High. Converts the map from "inspirational" to "actionable."
**Implementation:**
1. Add an optional `hours` object to the `venues.json` schema (keyed by day of week).
2. Build a small data-entry workflow: a GitHub Action or Python script that pre-populates hours from each venue's Google Business Profile JSON-LD (many venues expose this).
3. Add an "Open now" toggle to the FilterBar.
**Tools needed:** Python `requests`, `json-schema`, React state.
**Effort:** 2–3 days (data entry is the long tail, but it can be community-contributed incrementally).

### MVP 3: Venue submission form (Google Form → GitHub Issue)
**Impact:** High. Removes the biggest barrier to community contribution.
**Implementation:** A public Google Form with fields: venue name, address, website, events URL, venue type, region. On submit, a Google Apps Script (or Zapier free tier) creates a GitHub issue using the GitHub API. A maintainer reviews and merges the JSON addition.
**Tools needed:** Google Forms, GitHub Issues API, optionally Zapier or Make.
**Effort:** ~half a day.

### MVP 4: Prominent "This weekend" shortcut
**Impact:** Medium-high. Surfaces the site's most common use case.
**Implementation:** A single button in the FilterBar (or on the homepage header stats bar) that sets `datePreset = "weekend"`. Add a "weekend" preset to `lib/filters.js`.
**Tools needed:** React state change + one line in filters.js.
**Effort:** ~2 hours.

### MVP 5: Scraper health badge in the UI
**Impact:** Medium. Builds trust with users and helps maintainers.
**Implementation:** During the daily CI run, write a `scraper_status.json` file alongside `events.json` with each venue's last-success date and event count. Show a small indicator in the VenueList for venues whose scraper hasn't returned events in >14 days.
**Tools needed:** Python (already used), GitHub Actions artifact writing.
**Effort:** ~1 day.

### MVP 6: Static neighborhood guide pages (1–3 to start)
**Impact:** Medium-high for SEO and tourist use case. High editorial value.
**Implementation:** Static `.md` or `.jsx` pages for 1–3 neighborhoods (e.g., Chinatown/DTLA, Mid-Wilshire/Miracle Mile, West Hollywood). Hand-written, no scraping. Link from the map when a neighborhood cluster is clicked.
**Tools needed:** React Router (or hash-based routing already in place), markdown.
**Effort:** 1 day per neighborhood guide (writing + implementation), can be staggered.

---

## 9. Feature backlog (ship later)

Listed in rough priority order. None of these are blockers for value; they build on a healthy MVP foundation.

| Feature | Description | Complexity | Infrastructure |
|---|---|---|---|
| Weekly newsletter | Auto-generated "this week in LA art" email from events.json | Medium | Buttondown.email API (free tier) + GitHub Action |
| User saves (no login) | Browser `localStorage` favorites — heart icon on venue/event cards | Low | Zero — client only |
| Art fair calendar | Static JSON of LA's annual fairs (Frieze, Felix, NADA, etc.) + listing page | Low | Zero |
| "What's closing soon" view | Events ending within 7 days — high urgency discovery | Low | Zero — filter already in data |
| Exhibition image in listings | Scrape each venue's OG `og:image` tag and cache it | Medium | GitHub Actions artifact storage |
| Annual stats / data page | "Year in review" — count of events, most active venues, etc. — auto-generated from archive | Medium | GitHub Actions + static page |
| "Near me" geolocation | Browser geolocation API → sort venues by proximity | Low | Zero — client only |
| Artist index | Extract artist names from event titles, build a browsable index | Medium | Python NLP pass during CI |
| Mobile PWA | Add manifest.json + service worker for installability | Medium | Zero |
| Dark mode | Tailwind `dark:` variants throughout | Medium | Zero |
| Venue-level stats page | Individual venue pages showing event history from archive | Medium | Zero — data already exists |
| Scraper for open-data sources | LA County cultural calendar API, City of LA ICAL feeds | Low-Medium | Zero |
| Accessibility audit | WCAG 2.1 AA compliance pass | Medium | Zero |
| Multilingual support | Spanish UI (significant LA audience) | High | i18n library |
| Community contributions board | "Events added by community" feed, PR-to-submit workflow with better tooling | High | GitHub API |

---

## 10. On the gallery scraper question — direct answer

**Should you pull the gallery scrapers entirely?**

No, but reframe what they're *for.* The scrapers for commercial galleries don't differentiate Art in LA from Artforum or GP.LA — those platforms cover the commercial circuit better. But the scrapers serve two purposes that are still worth having:

1. **Calendar completeness.** A user who wants to see everything within 5 miles of their current location needs all venues on the map, not just the ones GP.LA members joined. Completeness is part of the site's identity.

2. **Independence.** If GP.LA goes down, if Artforum paywalls their LA listings, if a gallery gets dropped from their member network — you still have the data.

The question isn't "should we have gallery scrapers?" but "should we spend maintenance energy on gallery scrapers when they break?" The answer to that is: only for Tier 1 venues (see Section 7). When a blue-chip gallery scraper breaks, add it to backlog. When a community space scraper breaks, fix it this week.

**The sharper identity:** Art in LA should lean hard into being the *only* place that covers the full LA art ecosystem — from Gagosian to Self Help Graphics. That's the thesis. Everything else flows from it.

---

*Sources consulted: direct inspection of artguide.artforum.com, galleryplatform.la, ocula.com, galleriesnow.net, artweek.com, artnet.com, art-collecting.com (May 2026); galleryplatform.la/terms; artguide.artforum.com/robots.txt; artguide.artforum.com/artguide/help; Ninth Circuit ruling hiQ Labs v. LinkedIn (2022); Feist Publications v. Rural Telephone (1991); California CPRA.*
