# Watchlist

Everything the health checks found that was **not** fixed, and why. An item
here is not forgotten — it is being tracked deliberately.

Anything sitting here for three cycles has stopped being a minor issue and
should be raised with the owner even if it looked small at first.

---

## For the owner — decisions only you can make

Nothing yet.

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
