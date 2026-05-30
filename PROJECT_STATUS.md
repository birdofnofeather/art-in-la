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
