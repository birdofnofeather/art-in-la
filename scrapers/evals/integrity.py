"""Groups B, D, E and F — drift over time, data quality, and honest monitoring.

  GROUP B — did anything disappear quietly? Compares today against the last
  time these checks ran. This is the only way to catch slow bleeding: a venue
  losing a third of its events every week looks fine on any single day.

  GROUP D — is the monitoring itself honest? A status report claiming
  everything is green is worthless unless something checks the claim. These
  compare what the status report says against what the data shows.

  GROUP E — is what we publish well-formed? Duplicates, dead venues, events in
  the past, corrupted text.

  GROUP F — is the machinery still running and still consistent? The pipeline
  failing silently is the failure that already happened once, for ten days.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timedelta, timezone

from .. import storage
from ..classify import derive
from .model import Finding, PASS, FAIL, WARN, SKIP

_MOJIBAKE = re.compile(r"[\xc2-\xf4][\x80-\xbf]")
ROOT = storage.ROOT


def _parse(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# ── Group B: what changed since last time ─────────────────────────────────

def drift(events: list[dict], archive: list[dict], previous: dict | None) -> list[Finding]:
    findings: list[Finding] = []
    now = {"events": len(events), "archive": len(archive)}

    if not previous:
        return [Finding(
            "B0", "How has the data changed since the last check?", SKIP,
            "This is the first run, so there is nothing to compare against. "
            "From the next run onwards this section reports what moved.",
            numbers=now,
        )]

    before_events = previous.get("events", 0)
    before_archive = previous.get("archive", 0)
    before_ids = set(previous.get("upcoming_ids") or [])
    today_ids = {e["id"] for e in events if e.get("id")}

    # ── B1: did the archive shrink? ──────────────────────────────────────
    findings.append(Finding(
        "B1", "Has any of our record of past events been lost?",
        PASS if len(archive) >= before_archive else FAIL,
        (f"The archive holds {len(archive)} past events; last check it held "
         f"{before_archive}. It must only ever grow — once a venue takes an "
         f"event off its website we can never get it back, so a shrinking "
         f"archive is permanent, unrecoverable data loss."),
        numbers={"archive_now": len(archive), "archive_before": before_archive},
    ))

    # ── B2: did events vanish that should still be listed? ───────────────
    # Only counts events that were still in the future last time, so ordinary
    # events simply happening does not look like loss.
    still_future = before_ids & today_ids
    vanished = before_ids - today_ids
    future_horizon = previous.get("future_ids") or []
    unexplained = [i for i in future_horizon if i not in today_ids]
    share = len(unexplained) / len(future_horizon) if future_horizon else 0
    findings.append(Finding(
        "B2", "Did events that had not happened yet disappear from the site?",
        PASS if share <= 0.1 else (WARN if share <= 0.25 else FAIL),
        (f"{len(unexplained)} of {len(future_horizon)} events that were still in "
         f"the future last check are no longer listed ({share:.0%}). Some of that "
         f"is normal — venues cancel things and take them down — but a large "
         f"share means we are losing real events, not that Los Angeles cancelled "
         f"a quarter of its programming."),
        evidence=[f"{i}" for i in unexplained[:6]],
        numbers={"vanished": len(unexplained), "was_future": len(future_horizon),
                 "vanished_share": round(share, 3)},
    ))

    # ── B3: overall movement ─────────────────────────────────────────────
    change = ((len(events) - before_events) / before_events) if before_events else 0
    findings.append(Finding(
        "B3", "Has the overall number of events moved sharply?",
        PASS if abs(change) <= 0.3 else WARN,
        (f"{len(events)} events now, {before_events} at the last check "
         f"({change:+.0%}). A big move in either direction is worth explaining: "
         f"down usually means something broke, up can mean a parser has started "
         f"picking up menus or past events."),
        numbers={"events_now": len(events), "events_before": before_events,
                 "change": round(change, 3)},
    ))

    # ── B4: per-venue collapse ───────────────────────────────────────────
    before_by_venue = previous.get("by_venue") or {}
    now_by_venue: dict[str, int] = {}
    for ev in events:
        now_by_venue[ev.get("venue_id")] = now_by_venue.get(ev.get("venue_id"), 0) + 1
    collapsed = [
        (v, n, now_by_venue.get(v, 0)) for v, n in before_by_venue.items()
        if n >= 4 and now_by_venue.get(v, 0) <= n * 0.4
    ]
    findings.append(Finding(
        "B4", "Has any individual venue lost most of its events?",
        PASS if not collapsed else WARN,
        (f"{len(collapsed)} venue(s) are now publishing 40% or less of what they "
         f"published at the last check. A venue can legitimately empty out at the "
         f"end of a season, so this is a prompt to look rather than a verdict."),
        evidence=[f"{v}: {was} -> {now}" for v, was, now in collapsed[:8]],
        numbers={"collapsed_venues": len(collapsed)},
    ))
    return findings


def snapshot(events: list[dict], archive: list[dict]) -> dict:
    """What the next run needs in order to compare against this one."""
    now = datetime.now(timezone.utc)
    by_venue: dict[str, int] = {}
    for ev in events:
        by_venue[ev.get("venue_id")] = by_venue.get(ev.get("venue_id"), 0) + 1
    # Events at least 5 days out — far enough ahead that they should still be
    # listed at the next check three days from now.
    horizon = now + timedelta(days=5)
    return {
        "events": len(events),
        "archive": len(archive),
        "by_venue": by_venue,
        "upcoming_ids": [e["id"] for e in events if e.get("id")],
        "future_ids": [e["id"] for e in events
                       if e.get("id") and (_parse(e.get("start")) or now) >= horizon],
    }


# ── Group E: is the published data well-formed? ───────────────────────────

def quality(events: list[dict], venues: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    known = {v["id"] for v in venues if v.get("id")}
    now = datetime.now(timezone.utc)

    corrupted = [e for e in events
                 if _MOJIBAKE.search((e.get("title") or "") + (e.get("description") or ""))]
    findings.append(Finding(
        "E1", "Is any published text still garbled?",
        PASS if not corrupted else FAIL,
        (f"{len(corrupted)} events contain corrupted characters. This is the "
         f"'espaÃ±ol' bug — text read with the wrong alphabet. Zero is the only "
         f"acceptable answer, because the repair is automatic and anything "
         f"getting through means the repair stopped running."),
        evidence=[f"[{e['venue_id']}] {e.get('title','')[:60]}" for e in corrupted[:5]],
        numbers={"corrupted": len(corrupted)},
    ))

    ids = [e.get("id") for e in events]
    dupes = len(ids) - len(set(ids))
    findings.append(Finding(
        "E2", "Does the same event appear more than once?",
        PASS if not dupes else FAIL,
        f"{dupes} duplicate event ids. Each one shows a visitor the same event twice.",
        numbers={"duplicates": dupes},
    ))

    orphans = [e for e in events if e.get("venue_id") not in known]
    findings.append(Finding(
        "E3", "Does every event belong to a venue we actually know about?",
        PASS if not orphans else FAIL,
        (f"{len(orphans)} events reference a venue that is not in the venue list. "
         f"These cannot be shown on the map and break the venue page."),
        evidence=[f"{e.get('venue_id')}: {e.get('title','')[:50]}" for e in orphans[:5]],
        numbers={"orphans": len(orphans)},
    ))

    stale = []
    for ev in events:
        finish = _parse(ev.get("end")) or _parse(ev.get("start"))
        if finish and finish < now - timedelta(days=2):
            stale.append(ev)
    findings.append(Finding(
        "E4", "Are we still advertising events that already happened?",
        PASS if not stale else FAIL,
        (f"{len(stale)} events finished more than two days ago and are still on "
         f"the live list. Anyone planning from this would turn up to nothing."),
        evidence=[f"[{e['venue_id']}] {e.get('title','')[:50]} ended {e.get('end') or e.get('start')}"
                  for e in stale[:5]],
        numbers={"already_over": len(stale)},
    ))

    undated = [e for e in events if e.get("event_type") != "exhibition" and not e.get("start")]
    findings.append(Finding(
        "E5", "Does every event have a date?",
        PASS if not undated else FAIL,
        f"{len(undated)} non-exhibition events have no start date, so they cannot "
        f"be placed on a calendar at all.",
        numbers={"undated": len(undated)},
    ))

    typed = [e for e in events if e.get("event_type") == "other"]
    share = len(typed) / len(events) if events else 0
    findings.append(Finding(
        "E6", "How many events could we not put into any category?",
        PASS if share <= 0.2 else WARN,
        (f"{len(typed)} of {len(events)} events ({share:.0%}) are labelled 'other'. "
         f"A rising share means the wording rules are drifting behind how venues "
         f"actually describe things. This is a quality trend, not a breakage."),
        numbers={"other": len(typed), "other_share": round(share, 3)},
    ))

    # Recurring programmes that slipped through: same title, evenly spaced.
    from ..utils.recurring import has_regular_cadence, _as_date
    from ..utils.text import title_key
    groups: dict[tuple, list[dict]] = {}
    for ev in events:
        if ev.get("event_type") == "exhibition":
            continue
        groups.setdefault((ev.get("venue_id"), title_key(ev.get("title", ""))), []).append(ev)
    leaks = [(k, v) for k, v in groups.items()
             if len(v) >= 3 and has_regular_cadence([_as_date(e.get("start")) for e in v], 2, 3)]
    findings.append(Finding(
        "E7", "Are any weekly or monthly programmes still leaking onto the site?",
        PASS if not leaks else WARN,
        (f"{len(leaks)} title(s) still appear several times at regular intervals. "
         f"This is exactly the pattern of a standing class or tour — the thing "
         f"the recurring filter exists to hide — so anything here is a filter miss."),
        evidence=[f"[{k[0]}] {v[0].get('title','')[:55]} ×{len(v)}" for k, v in leaks[:6]],
        numbers={"leaking_series": len(leaks)},
    ))
    return findings


# ── Group D: is the monitoring telling the truth? ─────────────────────────

def monitoring(status: dict, events: list[dict], expectations: dict) -> list[Finding]:
    findings: list[Finding] = []
    if not status:
        return [Finding("D0", "Is there a status report at all?", FAIL,
                        "public/data/status.json is missing, so the daily run "
                        "never produced a verdict about its own health.")]

    rows = status.get("venues") or []
    published_by_venue: dict[str, int] = {}
    for ev in events:
        published_by_venue[ev.get("venue_id")] = published_by_venue.get(ev.get("venue_id"), 0) + 1

    # D1: does a "green" venue actually have events?
    lying_green = [r for r in rows
                   if r["verdict"] == "green" and published_by_venue.get(r["venue_id"], 0) == 0]
    findings.append(Finding(
        "D1", "Is the status report calling anything healthy that clearly is not?",
        PASS if not lying_green else FAIL,
        (f"{len(lying_green)} venue(s) are reported green while publishing nothing "
         f"at all. A monitor that reports a silent venue as healthy is worse than "
         f"no monitor, because it actively tells you not to look."),
        evidence=[r["venue_id"] for r in lying_green[:8]],
        numbers={"false_green": len(lying_green)},
    ))

    # D2: how noisy is it? A monitor nobody can act on is a monitor nobody reads.
    counts = status.get("counts") or {}
    total = sum(counts.values()) or 1
    noisy = (counts.get("yellow", 0) + counts.get("red", 0)) / total
    findings.append(Finding(
        "D2", "Is the status report quiet enough to be worth reading?",
        PASS if noisy <= 0.45 else WARN,
        (f"{counts.get('red',0)} red and {counts.get('yellow',0)} yellow out of "
         f"{total} venues ({noisy:.0%} flagged). If almost everything is flagged "
         f"every day, the report stops being information and becomes noise you "
         f"learn to skip — which is how the real failures get missed."),
        numbers={"flagged_share": round(noisy, 3), **counts},
    ))

    # D3: are the written expectations still plausible?
    impossible = []
    for vid, exp in expectations.items():
        lo, hi = exp.get("min_events"), exp.get("max_events")
        if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
            impossible.append(f"{vid}: minimum {lo} is above maximum {hi}")
    persistent = [r for r in rows
                  if any("fewer than the expected" in x for x in r.get("reasons", []))]
    findings.append(Finding(
        "D3", "Are the written expectations still sensible?",
        PASS if not impossible else FAIL,
        (f"{len(persistent)} venue(s) are missing their expected numbers. Where "
         f"that is the same venues run after run, either the venue really is "
         f"broken or the expectation was set too high — both need a decision, and "
         f"leaving it unresolved is what turns a monitor into wallpaper."),
        evidence=impossible[:5] or [r["venue_id"] for r in persistent[:8]],
        numbers={"below_expectation": len(persistent), "impossible": len(impossible)},
    ))
    return findings


# ── Group F: is the machinery still running? ──────────────────────────────

def pipeline(events: list[dict], raw: list[dict], status: dict) -> list[Finding]:
    findings: list[Finding] = []
    now = datetime.now(timezone.utc)

    stamps = [_parse(e.get("scraped_at")) for e in events if e.get("scraped_at")]
    newest = max((s for s in stamps if s), default=None)
    age = (now - newest).total_seconds() / 3600 if newest else None
    findings.append(Finding(
        "F1", "Is the daily scrape still running?",
        PASS if age is not None and age <= 36 else FAIL,
        (f"The freshest data is {age:.0f} hours old." if age is not None
         else "No event carries a timestamp, so we cannot tell when the scrape "
              "last ran.") +
        " The scrape is daily, so anything past 36 hours means it has stopped — "
        "and a stopped scrape is invisible from the website, which keeps serving "
        "the last good copy and looking perfectly healthy.",
        numbers={"hours_old": round(age, 1) if age is not None else None},
    ))

    findings.append(Finding(
        "F2", "Did the last run manage to publish?",
        PASS if status.get("published", True) else WARN,
        ("The last run published normally."
         if status.get("published", True) else
         "The last run REFUSED to publish and left the previous data on the site. "
         "That is the safety gate working as designed, but it means the site is "
         "showing older information until the underlying problem is fixed: "
         + "; ".join((status.get("fleet_checks") or {}).get("blocking") or [])),
        numbers={"published": bool(status.get("published", True))},
    ))

    # F3: is what we publish exactly what the rules produce from the harvest?
    # If not, something wrote to events.json outside the pipeline, and the next
    # legitimate run would silently undo it.
    if not raw:
        findings.append(Finding("F3", "Is the published data reproducible?", SKIP,
                                "No stored harvest to re-derive from."))
    else:
        rederived = derive(raw)
        published_ids = {e["id"] for e in events if e.get("id")}
        expected_ids = {e["id"] for e in rederived.upcoming if e.get("id")}
        drifted = published_ids ^ expected_ids
        findings.append(Finding(
            "F3", "Can the published list be reproduced exactly from the stored harvest?",
            PASS if not drifted else WARN,
            (f"{len(drifted)} event(s) differ between what is published and what "
             f"the rules produce from the stored harvest. Small differences are "
             f"normal — dates move on between the scrape and this check — but a "
             f"large number means something edited the published file directly, "
             f"and the next scrape would silently throw that edit away."),
            numbers={"difference": len(drifted), "published": len(published_ids),
                     "rederived": len(expected_ids)},
        ))

    # F4: the test suite and the rules self-check.
    for eid, cmd, question in [
        ("F4", ["python3", "-m", "pytest", "scrapers/tests", "-q"],
         "Does the test suite still pass?"),
        ("F5", ["python3", "-m", "scrapers.check_rules"],
         "Do the curation rules still agree with their own examples?"),
    ]:
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
            ok = proc.returncode == 0
            tail = (proc.stdout or proc.stderr).strip().splitlines()[-3:]
        except Exception as e:
            ok, tail = False, [f"could not run: {type(e).__name__}: {e}"]
        findings.append(Finding(
            eid, question, PASS if ok else FAIL,
            ("Passed." if ok else "FAILED — see the output below.") +
            (" The rules self-check is what stops a deliberate curation decision "
             "being quietly weakened." if eid == "F5" else ""),
            evidence=tail,
        ))
    return findings
