# Art in LA — Status & Next Steps (2026-05-30)

## Where the project is

A static site (React + Vite on GitHub Pages) backed by Python scrapers that run
on a daily GitHub Actions cron and commit fresh `events.json` / `archive.json`.
Repo: `github.com/birdofnofeather/art-in-la`. The local project folder **is** that
repo (origin set, HEAD was in sync with `origin/main`). There is no GitHub *API*
connector attached, so I can't read Actions run logs or open PRs through an API —
I work directly in the clone.

## Scrapers failing daily — what I found

- The scraper **code is healthy**. The full pipeline (scrape → reshape → recurring
  filter → dedupe → archive) runs cleanly locally; `run_all.py` already catches
  per-venue exceptions and always exits 0, so no single venue can fail the job.
- The **last successful data commit was 2026-05-02** (28 days stale). The bot
  committed daily Apr 25–May 2, then stopped — right as the May 3 batch of
  scraper/redesign changes landed.
- Because the code runs, the failure is in the **CI job**, not the Python. The
  `Commit` step had no `if: always()`, so any non-zero/hung run (e.g. a slow
  venue exhausting the job's time) silently skips the commit and looks like a
  daily failure. I can't confirm the exact CI error without the Actions logs.

**Hardening applied** to `daily-scrape.yml`: job `timeout-minutes: 30`, scrape
step `timeout-minutes: 20`, and `Commit` step set to `if: always()` so a partial
run still commits whatever was written.

## Scope change: museums + institutions only (galleries pulled)

Per your decision (keep museums + non-commercial institutions; remove commercial
galleries from the site entirely):

- **Archived 58 gallery scraper modules** to `scrapers/venues/_archived_galleries/`
  and removed their imports + `SCRAPERS` entries. Registry went **101 → 48** scrapers.
- **Removed 79 gallery venues** from `venues.json` (**159 → 80** venues: 31 museum,
  23 community, 17 alternative, 9 academic) and **purged 135 gallery events** plus
  their archive records.
- **Regenerated fresh data** with the trimmed set: **445 upcoming events** across
  42 venues, including **86 exhibitions** for the Exhibitions tab. No scraper warnings.

## Display fixes

- Removed `gallery` from the frontend taxonomy (`constants.js`) so no empty
  "Gallery" filter chip or legend swatch appears.
- Normalized 7 venues whose `type` was outside the UI taxonomy (`nonprofit`,
  `university`, `literary_arts_center`, `art_center`, `cultural_center`) into the
  four canonical buckets so their markers/labels render correctly — a pre-existing
  bug where those venues showed gray markers with `undefined` labels.
- Verified: no orphan events, every event's venue exists, every venue type is in
  the taxonomy, `constants.js` parses, registry imports the 48 scrapers, all JSON valid.

## Action needed from you

The changes are saved to the repo working tree but I **could not commit/push** —
the sandbox can't clear a stale `.git/index.lock` on the mounted folder. From your
machine:

```
cd "Art in LA"
rm -f .git/index.lock        # if it's still there
git add -A
git commit -m "Narrow scope to museums + institutions; archive gallery scrapers; harden daily cron"
git push origin main
```

## Suggested next steps (priority order)

1. **Confirm the CI fix.** After pushing, run **Actions → Daily scrape → Run
   workflow** manually and watch it commit. If it still fails, the log will now
   show whether it's the scrape step (timeout) or the push step (token/branch
   protection — check Settings → Actions → Workflow permissions = Read and write).
2. **Add a scraper health check.** A tiny CI assertion that fails loudly if a
   venue returns 0 events for N consecutive days, so silent rot surfaces fast.
3. **Re-home the map center/zoom** now that the venue set is smaller and more
   museum-weighted (`VenueMap.jsx` `CENTER`/`ZOOM`).
4. **Decide on the ~38 institutions with no scraper** (80 venues, 48 scrapers):
   either write scrapers or mark them "listing only" in the UI.
5. **Prune `competitive-analysis.md` / `recommendations.html`** references to
   galleries if you want the docs to match the new scope.

---

## Round 3 — scraper health, efficiency, and a "Today" view (2026-05-30)

### Health check: all 48 scrapers run individually

6 returned zero events. Fixed the two highest-impact ones; the rest are
JavaScript-rendered with no CI-reachable API (documented below).

| Scraper | Was | Now | Fix |
|---|---|---|---|
| armory_pasadena | 0 (403) | 36 | Browser User-Agent (site blocked the bot UA) |
| the_broad | 0 (JS) | 19 incl. 10 exhibitions | New scraper on Drupal JSON:API (`/jsonapi/node/nextgen_event` + `nextgen_exhibition`) |
| norton_simon | 0 | 0 | JS-rendered, WP REST disabled — needs rendering (see proposals) |
| huntington | 0 | 0 | Next.js + Vercel bot protection (429) — needs rendering |
| ica_la | 0 | 0 | JS-rendered headless CMS, no public API |
| corita_art_center | 0 | 0 | Webflow, server-rendered — fixable later by updating selectors |

### Efficiency improvements

- **Parallel scraping.** `run_all` now scrapes venues concurrently (thread pool,
  `SCRAPE_WORKERS` env, default 8). A full 48-venue run dropped from timing out
  past ~60s to **~27s**. Output is deduped/sorted afterwards so order is stable.
- **Browser User-Agent** at the HTTP layer fixed 403/429 blocks (Norton Simon,
  Armory, and likely others that were silently thin).
- Confirmed `dedupe` is already O(n); `lamag` is slow (~21s) only because it
  fetches each exhibition detail page — acceptable, and now overlapped with other
  venues by the thread pool.

### New feature: "Today"

- Added a **Today** date preset (events) — shows everything happening today.
  Exhibitions already have **On view now**, which is today's on-view set.
- Hardened date filtering so undated events no longer leak into any date window.

### Proposed next improvements

1. **Render the 3 JS-only venues** (Norton Simon, Huntington, ICA LA): add a
   single optional Playwright/Browserless step in CI that renders those pages and
   hands HTML to the existing parsers. Keeps the rest of the pipeline pure-requests.
2. **True showtimes** for Academy Museum / REDCAT via their Ticketure feeds.
3. **Fix corita** by updating its Webflow selectors (quick).
4. **Scraper health gate** in CI: fail/alert if a venue returns 0 for N days, so
   silent breakage surfaces immediately.

---

## Round 5 — JS-rendered museums revisited via live browser (2026-05-31)

Used a connected browser to inspect the three zero-event museums' actual network
traffic and rendered DOM, then implemented pure-`requests` scrapers where possible.

| Venue | Verdict | Result |
|---|---|---|
| **ica_la** | Spree (Rails), genuinely **server-rendered** — events are in the HTML | **Fixed.** New scraper parses `.calendar__month` → `.calendar-event`. Live now. |
| **norton_simon** | **Cloudflare-gated** (`server: cloudflare`, `cf-ray`): a real browser gets the full page, `requests` gets an event-less shell | Not fixable via requests. Needs a real browser at runtime. |
| **huntington** | **Vercel bot protection** — returns HTTP 429 to scripted clients | Not fixable via requests. Needs a real browser at runtime. |

Key correction to the earlier note: Norton Simon and Huntington aren't merely
"JS-rendered" — they actively serve different content to non-browser clients
(bot management). A headless Playwright step may still hit the Cloudflare/Vercel
challenge, so these two are best treated as "listing only" links unless a
challenge-solving render service is used.

Net coverage now: **45 venues produce events** (was 43). The two bot-gated
museums are the only remaining gap and are documented in their scraper files
(`# BLOCKED-NOTE`).
