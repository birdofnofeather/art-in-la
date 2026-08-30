# Eval logbook

What this is: every few days the whole system is checked against a fixed
set of questions, and the answers are written here, newest first. It
exists so that a problem which appears slowly — a venue quietly losing
half its events each week — becomes visible, which no single day's
snapshot can do.

The checks marked 🌐 compare us against the venues' own websites. Those
are the only ones that can catch us being confidently wrong; the rest
compare our code against itself and can only catch a change.

Run it yourself with `python -m scrapers.evals`.

---

## 2026-08-30 — PASS

22 passed, 0 failed, 0 need watching, 1 could not run.

### Nothing is broken

Every check that can fail, passed.

### Checked against the outside world

3 of these checks compared us against the venues' own websites rather than against our own code. They all passed.

### Every check

| | Check | Result |
|---|---|---|
| `A1` 🌐 | Do the events we publish actually appear on the venue's own page? | **PASS** |
| `A2` 🌐 | Does each event's date actually appear on the venue's page? | **PASS** |
| `A3` 🌐 | Do the links we publish still work? | **PASS** |
| `B0`  | How has the data changed since the last check? | **----** |
| `C1`  | Does the safety gate still refuse to publish obviously broken data? | **PASS** |
| `C2`  | Do the text-quality rules still catch unreadable text? | **PASS** |
| `C3`  | Are the curation decisions you made on purpose still holding? | **PASS** |
| `D1`  | Is the status report calling anything healthy that clearly is not? | **PASS** |
| `D2`  | Is the status report quiet enough to be worth reading? | **PASS** |
| `D3`  | Are the written expectations still sensible? | **PASS** |
| `E1`  | Is any published text still garbled? | **PASS** |
| `E2`  | Does the same event appear more than once? | **PASS** |
| `E3`  | Does every event belong to a venue we actually know about? | **PASS** |
| `E4`  | Are we still advertising events that already happened? | **PASS** |
| `E5`  | Does every event have a date? | **PASS** |
| `E6`  | How many events could we not put into any category? | **PASS** |
| `E7`  | Are any weekly or monthly programmes still leaking onto the site? | **PASS** |
| `F1`  | Is the daily scrape still running? | **PASS** |
| `F2`  | Did the last run manage to publish? | **PASS** |
| `F3`  | Can the published list be reproduced exactly from the stored harvest? | **PASS** |
| `F4`  | Does the test suite still pass? | **PASS** |
| `F5`  | Do the curation rules still agree with their own examples? | **PASS** |
| `G1`  | Can these checks still detect a problem when there is one? | **PASS** |

---
### Notes from this run

First cycle — the check suite itself was built this session, so this run is the baseline. One real bug found and fixed: Wende Museum's weekly picture-book workshop was appearing three times on the site. The filter that hides weekly programmes demanded every gap between dates be near-identical, and this workshop skipped a week (gaps of 14, 7, 7 days), so the whole series escaped. It now reads a 14-day gap as 'two weeks'. Getty's standing 'Exhibition Tour' was leaking the same way and is now hidden; Getty's curator's tour now shows as one listing with its other dates noted.

---

