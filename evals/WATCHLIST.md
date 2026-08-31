# Watchlist

Everything the health checks found that was **not** fixed, and why. An item
here is not forgotten — it is being tracked deliberately.

Anything sitting here for three cycles has stopped being a minor issue and
should be raised with the owner even if it looked small at first.

---

## Settled: the weekly Claude session cannot work, and has been removed

A scheduled Claude session was set up to diagnose and repair problems each week.
It cannot save its work, and this is not fixable from inside it.

The exact error, from its run on 31 August:

    access denied by the git proxy: birdofnofeather/art-in-la is not in this
    session's authorized repository set, so the proxy will not inject a
    credential for it.

A session started by a schedule does not inherit permission to write to this
project, and it has no way to grant itself that permission either. It would have
cost about $11 a week to produce work that evaporated when it finished.

The schedule has been deleted. Everything that must happen without a person
present now runs in GitHub Actions, which is free and provably can save its
results. Repairs happen when the owner opens a session and asks.

If the owner wants the weekly session back, the one thing that might work is
creating it from the Routines screen on claude.ai rather than from inside a
session, where the project can be attached as a source with write access. Worth
one attempt; not worth a second if it fails the same way.

---

## For the owner — decisions only you can make

**1. Is 8 exhibitions the right expectation for LACMA?**
I set expected exhibition counts by hand for 21 museums, guessing from what
those museums typically have on. They drive the "this venue's exhibitions are
missing" reporting. If any number is wrong the report will be wrong in the same
direction forever. Nothing breaks if they stay as they are — the gap is real
either way — but if you happen to know that, say, the Autry usually has two
shows rather than three, the numbers live in `scrapers/expectations.json` and I
can adjust them. No rush.

**2. Should a curator's tour that runs four times appear once or four times?**
Currently: once, with "Also on Oct 6, Nov 17, Dec 9" shown beside it. The
alternative is four separate listings. I chose once because four copies of the
same tour push genuine one-off events off the page, but this is a judgement
about what the site is for rather than a technical question. Getty's
*Instante/revelación* curator's tour is the live example.

---

## Their problem — venue websites down, blocking us, or moved

*A venue that cannot be reached is not a broken scraper. Rewriting code because
a website is refusing to answer produces confident, wrong changes to code that
was never broken. Several of these work fine from GitHub's servers and only
fail from other addresses, so the source of the failure matters.*

| Venue | First seen | What happens | Notes |
|---|---|---|---|
| Norton Simon | 2026-08-30 | Refuses our requests (403) from outside GitHub | Scraped through a real browser in the nightly run; works there |
| Huntington | 2026-08-30 | Returns a "too many requests" holding page | Same — its security check clears itself after a few seconds in a real browser |
| MOCA Grand | 2026-08-30 | Connection times out | Also currently producing no events; see below |
| Arroyo Arts | 2026-08-30 | Connection refused | Has never produced events |

---

## Parked venues — repair attempted, not yet successful

*Nothing parked yet. When a venue is parked, record what was tried so the next
cycle does not repeat it.*

| Venue | Parked on | Attempts | What was tried | What was observed |
|---|---|---|---|---|

---

## Known broken, not yet attempted

These were already silent before this work began. They are listed so their age
is visible — a venue quietly dead for two months is a different problem from one
that broke yesterday.

| Venue | Last produced events | Silent for |
|---|---|---|
| SCI-Arc | 2026-07-11 | ~7 weeks |
| Beyond Baroque | 2026-07-18 | ~6 weeks |
| ESMoA | 2026-07-21 | ~6 weeks |
| Torrance Art Museum | 2026-07-23 | ~5 weeks |
| Self Help Graphics | 2026-08-08 | ~3 weeks |
| ArtCenter | 2026-08-08 | ~3 weeks |
| MOCA Grand | 2026-08-10 | ~3 weeks |
| MOCA Geffen | 2026-08-10 | ~3 weeks |
| ICA LA | 2026-08-23 | ~1 week |
| LA Municipal Art Gallery | 2026-08-27 | days |

---

## The exhibitions gap — the largest known hole

Twenty-six venues publish events and **zero** exhibitions, including most of the
largest museums in Los Angeles: LACMA, Hammer, Huntington, Autry, Skirball,
JANM, Fowler, MOLAA, Norton Simon.

The cause is structural rather than a bug. Museums list their shows on a
separate exhibitions page, and a survey of all 85 venues found **not one** with
a machine-readable exhibitions feed. The plumbing to read such a feed exists and
costs nothing, but there is nothing to read.

What has changed: it is no longer invisible. Expected exhibition counts are
recorded by hand for 21 museums, so the shortfall is reported on every run
instead of a venue with events looking healthy.

Closing it properly needs the AI extraction tier — reading the exhibitions page
as text and pulling the shows out of it. That is a later phase.

---

## Cleared — resolved, kept for the record

| Date | What it was | How it was resolved |
|---|---|---|
| 2026-08-30 | Wende Museum's weekly "Illustrating Picture Books" workshop appeared three times in the events list | The filter that hides weekly programmes demanded every gap between dates be near-identical. This workshop skipped a week, giving gaps of 14, 7 and 7 days, so the whole series escaped. The filter now reads 14 days as "two weeks" and catches it. Found by the very first eval run. |
| 2026-08-30 | LMU's Laband Gallery was reported healthy while showing visitors nothing | It scraped events successfully, so every health check was satisfied — but all of them were filtered out before publication, leaving the venue blank on the site. A venue that scrapes something and publishes nothing is now flagged. |
| 2026-08-30 | The daily status report was flagging 59% of venues, which makes it something you learn to skip | Two causes. Fifteen of the flags were the known exhibitions gap, repeated as fresh news every day — it is now counted once as a number instead. Twelve were venues "drifting from their recent average" when that average was built from two days of data; drift is now only judged once there are at least four runs to compare against. Now flagging 31%. |
| 2026-08-31 | The Museum of Tolerance was reported healthy while its page on the site was empty | It landed just under every alarm at once: two silent days where the alarm needs three, no upcoming dates on its own website so the page comparison declined to judge, and nothing scraped that day so the "scraped something but published nothing" check did not apply. Every check declined and the silence read as health. A venue showing visitors nothing is now never green. Of the seventeen venues currently publishing nothing, sixteen were already flagged — so this added exactly one, not a wave of noise. |
| 2026-08-31 | The nightly scrape had not run, and no alarm had noticed | GitHub delays scheduled jobs on free projects — this one has started anywhere between 7:33am and 1:02pm on different days, and sometimes skips entirely. The staleness alarm waits 36 hours and the data was only 26 hours old, so it stayed quiet, correctly. Triggered by hand; the site is current again. The lesson is that "no alarm" does not mean "the scrape ran today". |
