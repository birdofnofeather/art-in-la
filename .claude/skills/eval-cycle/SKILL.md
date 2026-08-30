---
name: eval-cycle
description: Run the Art in LA health checks, diagnose whatever they find, fix what is safely fixable, and write up the result in the logbook. Use when running a scheduled check-up on the scrapers, when asked to check whether the site's data is healthy, or when the phrase "eval cycle" / "eval run" appears.
---

# The eval cycle

## Who does what

The checks run in TWO places, and the split matters.

**GitHub Actions runs the checks every three days and commits the results.**
That is the guaranteed floor: it is free, it provably can commit, it needs no
judgement, and it happens whether or not anything else works. By the time you
read this, `evals/LOGBOOK.md` already has the latest answers in it.

**You do the part that needs thinking**: working out WHY something failed and
repairing it. You cost about $11 a session, so you run weekly rather than every
three days, and you should not waste that on re-running checks a free workflow
has already run.

So: read the logbook first. Only re-run the checks yourself if you have changed
something and need to see the effect, or if the recorded run looks wrong.

This split exists because the first test of this Routine did 36 minutes of work
and pushed nothing — no commit, no branch, no record. If your push fails, say so
loudly and early; do not spend an hour working and then discover it at the end.

## What this is for

Art in LA scrapes about sixty museum and arts-organisation websites every night
and publishes what it finds. Nobody reads those sixty websites to check the
result. This procedure is the substitute for that reading: a fixed set of
questions asked every few days, an honest answer written down each time, and a
small, careful repair when an answer is wrong.

The person who owns this project does not have time to check the scrapers. So
the job is to find the problem, fix it if fixing is safe, prove the fix worked,
and write down what happened. Only escalate when a decision genuinely belongs
to them — and try at least two approaches of your own first.

## Rules you may not break

These exist because the tempting shortcut, every single time, is to make the
check pass rather than make the thing work.

**Never edit these to make a check pass:**

| File | Why it is protected |
|---|---|
| `scrapers/rules.yaml` | Holds every curation decision. Weakening the recurring filter instantly "fixes" a low event count and silently undoes deliberate exclusions — Getty's garden tour, LACMA's gallery tours, Pieter's weekly dance classes. |
| `public/data/venues.json` | The hand-curated venue list. Adding or removing a venue is an editorial decision, not a repair. |
| `scrapers/tests/**` | You may ADD tests. Never weaken, skip, or delete one to get to green. |
| `.github/workflows/**` | The automation must not be able to loosen its own safety checks. |
| `scrapers/expectations.json` entries marked `"source": "human"` | Deliberate statements about what a venue should produce. |

Fuller detail: `.github/RULES_ARE_OFF_LIMITS.md`.

**Every code fix must come with a test that fails before the fix and passes
after.** If you cannot write that test, you do not yet understand the problem
well enough to fix it — investigate more, or record it and move on.

**Never delete data to make a number look better.** In particular the archive
of past events can never be re-scraped: once a venue takes an event off its
website it is gone forever.

## The procedure

### Step 1 — Get the current state

```bash
cd /home/user/art-in-la
git checkout main && git pull --ff-only origin main
pip install -q -r scrapers/requirements.txt && pip install -q pytest
```

Check the nightly scrape is actually running — this is the failure that already
happened once, silently, for ten days:

```bash
python3 -c "
import json, collections
e = json.load(open('public/data/events.json'))
print(collections.Counter((x.get('scraped_at') or '')[:10] for x in e).most_common(3))"
git log --oneline -5
```

If the newest data is more than about 36 hours old, the scrape has stopped.
That is the first thing to fix, ahead of everything else — every other check is
reading stale data and its answers do not mean much.

### Step 2 — Prove you can push, BEFORE doing any work

This costs ten seconds and saves an hour. The first test run of this Routine
worked for 36 minutes and then produced nothing durable.

```bash
git commit --allow-empty -m "chore(evals): connectivity check" && git push origin main
```

If that fails, STOP. Do not do the cycle. Report the exact error as your entire
answer — the owner needs to know that the automation cannot save its work, and
that is more important than any scraper finding. If it succeeds, carry on; the
empty commit is harmless.

### Step 3 — Read what the workflow already found

```bash
head -60 evals/LOGBOOK.md
```

The GitHub Actions run has already executed every check and written the answers
there. Start from that rather than re-running everything.

Re-run the checks yourself only when you need to:

```bash
python3 -m scrapers.evals --seed 7 --no-write 2>&1 | tail -60
```

Use the fixed `--seed` so the sample of events verified against venue websites
is repeatable.

**Read `G1` first.** It plants deliberate faults and confirms the checks notice
them. If `G1` fails, every other "pass" in the report is unreliable and fixing
`G1` is the only work worth doing that cycle.

### Step 4 — Sort what came back

Take each `FAIL` and `WARN` in turn and put it in one of five boxes. Guessing
the box wrong is the main way this procedure goes wrong, so work through them
in order:

**Box 1 — the check itself is wrong.** Before believing any finding, reproduce
it by hand. Print the actual records. A check that flags well-behaved data is a
bug in the check, and fixing the pipeline to satisfy a broken check makes the
system worse. This has already happened twice: an early version of the monitor
compared published counts against the venue's page and flagged eleven perfectly
healthy venues, because curation removes events on purpose.

*Do:* fix the check, add a test for the case it got wrong, and say so plainly in
the logbook. Never quietly loosen a threshold — that is the same mistake in the
opposite direction.

**Box 2 — their website, not our code.** The venue is down, blocking us, or has
moved. Signals: the page cannot be fetched at all, or returns a challenge page,
or `status.json` lists the venue under `unreachable`.

*Do:* record it on the watchlist. Do **not** rewrite a scraper whose website is
simply refusing to answer — you will produce confident, wrong changes to code
that was never broken. Several venues block data-centre addresses and work
perfectly from GitHub's servers, so check whether it works there before
concluding anything.

**Box 3 — a real bug in shared code.** Something in the pipeline is wrong for
everyone: dates, deduplication, the recurring filter, the quality rules.

*Do:* fix it. Write the failing test first. Then run
`python3 -m scrapers.reclassify --dry-run` and read what would change across the
whole dataset before applying — a shared-code change touches every venue at
once, which is exactly the kind of damage no per-venue check can see.

**Box 4 — one venue's scraper has broken.** Its website changed shape.

*Do:* attempt a repair, but cap yourself at **two attempts**. Fetch the page,
find what changed, fix that venue's file only, and confirm the venue produces a
sensible number of events. If two attempts fail, park it: record it on the
watchlist with what you tried and what you observed. A third speculative attempt
is worse than an honest "I could not fix this".

**Box 5 — a question about what the site should do.** "Should a curator's tour
that runs four times appear once or four times?" "Is 8 the right number of
exhibitions to expect from LACMA?"

*Do:* not decide alone. Record it in `evals/WATCHLIST.md` under "For the owner"
with the options and your recommendation. These are editorial choices about what
the site is for, and quietly making them is how a tool drifts away from what its
owner wanted.

### Step 5 — Prove the fix

```bash
python3 -m pytest scrapers/tests -q
python3 -m scrapers.check_rules
python3 -m scrapers.reclassify --dry-run     # what changed fleet-wide?
python3 -m scrapers.evals --offline --no-write   # did the finding clear?
```

For a change to a single venue, confirm it against the live site:

```bash
python3 -m scrapers.run_all --only <venue_id> --dry-run
```

Sanity-check the count. A scraper suddenly returning 300 events is as broken as
one returning zero — it has usually started reading the navigation menu.

### Step 6 — Write it down and commit

Record the run:

```bash
python3 -m scrapers.evals --seed 7 --notes "what you found, fixed, and left alone"
```

Then commit to `main` (the owner is the only developer and asked for this
directly — do not open a branch):

```bash
git add -A
git commit -m "evals: <what changed>"
git push -u origin main
```

The commit message should say what the check found, why it happened, and what
you did — in plain language. It is the only durable record of the reasoning.

### Step 7 — Update the watchlist

`evals/WATCHLIST.md` holds everything not fixed this cycle:

- **Parked venues** — repair attempted and failed, with what was tried.
- **Their problem** — venue websites down or blocking us, with the date first seen.
- **For the owner** — decisions only they can make.
- **Cleared** — items resolved, kept so a recurring problem is recognisable.

An item sitting on the watchlist for three cycles has become a real problem and
should be raised with the owner even if it once looked minor.

## Writing for the owner

They are not a programmer, and jargon in these reports has been a real problem.
Every logbook entry and commit message must be readable by someone who has never
seen the code.

- Say what a visitor to the site would experience, not what the code does.
  "Three copies of the same weekly workshop were filling the events list" beats
  "the cadence detector's tolerance check rejected non-uniform gaps".
- Name the venue. "Wende Museum" beats "a venue".
- Give the number that matters. "383 events, down from 394" beats "counts moved".
- Say what you decided NOT to do and why. Silence reads as "nothing to see".
- No abbreviations that only make sense inside the project.

## Budget

The checks themselves cost nothing — no AI model is called. The only cost is
this session's own reasoning. Keep a cycle to well under an hour of work: run
the checks, fix at most two or three things properly, and record the rest.
Depth on a few real problems beats a shallow pass at everything.

## What "working perfectly" means

Do not expect all green. A realistic healthy cycle looks like:

- `G1` passes — the checks can still detect problems.
- No `FAIL` in groups C, E or F — the safety equipment is armed, the published
  data is well-formed, the machinery is running.
- Group A (checked against the venues' own websites) shows most sampled events
  really appearing on their pages.
- Some yellows, steady or shrinking over cycles, each one explained on the
  watchlist rather than ignored.

The number that matters over the two-week run is not how many checks pass on any
one day. It is whether the same problem keeps coming back — that means the fix
addressed a symptom rather than a cause, and it is worth reopening.
