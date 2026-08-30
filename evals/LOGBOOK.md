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

BASELINE CYCLE. The check suite itself was built this session, so this is the starting point rather than a routine run. Run against the nightly scrape's own data, not a local one — many venues refuse requests from this sandbox's address while allowing GitHub's servers, so local numbers were an artefact.

Verification against the venues' own websites: 22 of 23 sampled events were found on the page they link to (96%), 21 of 23 had their date visible (91%), 2 of 25 links could not be opened (8%). This is the first time anything in the project has checked that what we publish is real.

Four problems found and fixed this cycle:
1. Wende Museum's weekly picture-book workshop appeared three times on the site. The filter that hides weekly programmes required every gap between dates to be near-identical; this one skipped a week (14, 7, 7 days) so the whole series escaped. Getty's standing Exhibition Tour was leaking the same way.
2. LMU's Laband Gallery was reported healthy while showing visitors nothing — it scraped events but published none of them.
3. The status report was flagging 59% of venues, which is the point at which people stop reading it. Fifteen flags were the known exhibitions gap repeated daily; it is now counted once. Twelve were drift judged against a two-day-old average.
4. A clean run where one check had no data yet was headlined SKIP, which reads like a failure.

Nothing parked. Nothing needing the owner urgently; two judgement calls recorded on the watchlist.

---

