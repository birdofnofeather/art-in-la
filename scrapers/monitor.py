"""Does the system know whether it is working?

The old answer was no. The only question anything asked was "did this venue
return zero events?", which is why LACMA could publish 4 events and 0
exhibitions for months while looking perfectly healthy, and why six Getty
events sat on the live site with mangled Spanish in their titles.

You cannot detect breakage by examining your own output. You need something
independent to compare it against. This module asks three questions per venue,
from three different directions, and a venue is only green when all three agree.

  WITNESS 1 — THE SOURCE PAGE.  How many UPCOMING dates does the venue's own
  page advertise? If the page offers 24 and we harvested none, that is a break
  — even though the venue is reachable and nothing threw an error. This is the
  strongest signal because it compares us against the venue rather than against
  ourselves, and it costs one extra page fetch.

  It is measured against what we HARVESTED, never what we published: curation
  deliberately removes things, and Pieter publishes 4 of its 47 listings
  because the rest are weekly dance classes we hide on purpose.

  WITNESS 2 — RECENT HISTORY.  What did this venue produce over the last few
  runs? A sharp drop, a sharp spike, or a collapse in how many events carry
  descriptions or links is suspicious even when the count is non-zero.

  WITNESS 3 — A WRITTEN EXPECTATION.  scrapers/expectations.json records what
  normal looks like for each venue: roughly how many events, roughly how many
  exhibitions. Reality is checked against it.

The output is one verdict per venue plus one for the fleet, written to
public/data/status.json for the status page.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from . import storage
from .utils.http import get
from .utils.validate import quality_report

# Verdicts, worst first.
RED, YELLOW, GREEN = "red", "yellow", "green"
_RANK = {GREEN: 0, YELLOW: 1, RED: 2}

# A date written the way a venue writes one: "September 12", "Sep 12, 2026",
# "9/12/2026", "2026-09-12".
_DATE_ON_PAGE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b"
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

# Below this many FUTURE dates a page is too sparse to judge — it may genuinely
# have nothing coming up, and calling that a break would cry wolf daily.
MIN_DATES_TO_JUDGE = 6

# A page this rich in future dates, from which we harvested almost nothing,
# is a strong signal even short of zero.
RICH_PAGE = 20
NEAR_NOTHING = 2

# A venue's count moving by more than this against its recent average -> yellow.
DRIFT_TOLERANCE = 0.6

# ...but only once there are enough past runs for "average" to mean anything.
MIN_HISTORY_FOR_DRIFT = 4


def _worst(*verdicts: str) -> str:
    return max(verdicts, key=lambda v: _RANK.get(v, 0))


# ── Witness 1: what the venue's own page appears to offer ─────────────────

def count_future_dates_on_page(url: str) -> int | None:
    """How many distinct FUTURE dates the events page advertises. None if unreachable.

    Deliberately crude — it is not parsing events, only answering "does this
    page look like it is advertising things that have not happened yet?", which
    is enough to catch a parser that has stopped seeing them.

    Counting only future dates matters. Nearly every venue lists its past events
    below its upcoming ones, so a raw date count says almost nothing: MAK Center
    shows 67 dates for 3 upcoming events, and las_fotos_project shows 35 for 1.
    Comparing against those numbers flags healthy venues as broken every day,
    and a monitor that cries wolf daily is worse than no monitor at all.
    """
    if not url:
        return None
    resp = get(url)
    if resp is None or not resp.ok:
        return None
    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    text = (soup.find("main") or soup.body or soup).get_text(" ", strip=True)

    today = datetime.now(timezone.utc).date()
    horizon = today.replace(year=today.year + 2)
    future = set()
    for raw in set(_DATE_ON_PAGE.findall(text)):
        parsed = _parse_loose_date(raw, today)
        if parsed and today <= parsed <= horizon:
            future.add(parsed)
    return len(future)


def _parse_loose_date(raw: str, today):
    """Parse a date fragment as a venue would write it. None if it isn't one."""
    try:
        from dateutil import parser as dateparser
        # A bare "September 12" has no year; assume the next such date.
        parsed = dateparser.parse(raw, default=datetime(today.year, 1, 1)).date()
        if parsed < today and not re.search(r"\d{4}", raw):
            parsed = parsed.replace(year=today.year + 1)
        return parsed
    except Exception:
        return None


# ── Witness 2: recent history ─────────────────────────────────────────────

def _recent_average(history: list[int]) -> float | None:
    values = [v for v in history if isinstance(v, int)]
    return sum(values) / len(values) if values else None


# ── The per-venue assessment ──────────────────────────────────────────────

def assess_venue(venue_id: str, produced: list[dict], published: list[dict],
                 health: dict, expectation: dict, dates_on_page: int | None,
                 unreachable: bool = False) -> dict:
    """Three witnesses, one verdict, and the reasons in plain English.

    `unreachable` means the page probe could not fetch the venue's site at all.
    That is triage, and it matters more than it looks: a scraper returning
    nothing because the website is down or blocking us is a completely
    different problem from a scraper whose parsing has broken, and only the
    second is ours to fix.
    """
    reasons: list[str] = []
    known_gaps: list[str] = []
    verdict = GREEN

    events = [e for e in published if e.get("event_type") != "exhibition"]
    exhibitions = [e for e in published if e.get("event_type") == "exhibition"]
    n_total = len(published)

    # ── Witness 1 ────────────────────────────────────────────────────────
    # Compared against what we HARVESTED, never what we published. Curation
    # deliberately removes things — Pieter's page advertises 47 dates and we
    # publish 4 because the other 43 are weekly dance classes we hide on
    # purpose. Judging published counts against the page marks every
    # well-curated venue as broken.
    n_harvested = len(produced)
    if dates_on_page is not None and dates_on_page >= MIN_DATES_TO_JUDGE:
        if n_harvested == 0:
            verdict = RED
            reasons.append(
                f"the venue's page advertises {dates_on_page} upcoming dates "
                f"but we extracted nothing"
            )
        elif dates_on_page >= RICH_PAGE and n_harvested <= NEAR_NOTHING:
            verdict = _worst(verdict, YELLOW)
            reasons.append(
                f"the venue's page advertises {dates_on_page} upcoming dates but we "
                f"extracted only {n_harvested} — the parser may be reading the wrong "
                f"part of the page"
            )

    # ── Witness 2 ────────────────────────────────────────────────────────
    # A "recent average" built from one or two runs is not an average, it is
    # noise. Twelve venues were flagged for drifting from a history that was
    # two days old. Wait for a real baseline before judging movement.
    history = [v for v in (health.get("recent_counts") or []) if isinstance(v, int)]
    average = _recent_average(history) if len(history) >= MIN_HISTORY_FOR_DRIFT else None
    if average and average >= 3:
        change = (n_total - average) / average
        if change <= -DRIFT_TOLERANCE:
            verdict = _worst(verdict, YELLOW)
            reasons.append(
                f"produced {n_total}, well below its recent average of {average:.0f}"
            )
        elif change >= DRIFT_TOLERANCE * 3:
            verdict = _worst(verdict, YELLOW)
            reasons.append(
                f"produced {n_total}, far above its recent average of {average:.0f} — "
                f"possibly picking up navigation or a different page"
            )

    streak = int(health.get("zero_streak") or 0)
    if streak >= 3 and health.get("last_success"):
        if unreachable:
            # THEIR problem, not ours. Sending an automated repair at a scraper
            # whose website is simply refusing us produces confident, wrong
            # changes to code that was never broken. Several venues block
            # datacenter IP ranges and work perfectly from elsewhere.
            verdict = _worst(verdict, YELLOW)
            reasons.append(
                f"no events for {streak} runs, but the website could not be "
                f"reached at all — this looks like their site or a block on our "
                f"address, not our parser"
            )
        else:
            verdict = RED
            reasons.append(
                f"no events for {streak} consecutive runs "
                f"(last produced {health['last_success']})"
            )

    # ── Witness 3 ────────────────────────────────────────────────────────
    if expectation:
        lo, hi = expectation.get("min_events"), expectation.get("max_events")
        if isinstance(lo, int) and len(events) < lo:
            verdict = _worst(verdict, YELLOW)
            reasons.append(f"{len(events)} events, fewer than the expected {lo}")
        if isinstance(hi, int) and len(events) > hi:
            verdict = _worst(verdict, YELLOW)
            reasons.append(f"{len(events)} events, more than the expected {hi}")
        min_exh = expectation.get("min_exhibitions")
        if isinstance(min_exh, int) and min_exh > 0 and len(exhibitions) < min_exh:
            # A gap we already know about, have written down, and cannot close
            # until the extraction tier exists is reported ONCE for the whole
            # fleet, not as a fresh yellow against fifteen venues every single
            # day. Repeating known news is how a status report becomes wallpaper
            # and real problems start getting skipped over.
            if expectation.get("known_gap") == "exhibitions":
                known_gaps.append("exhibitions")
            else:
                verdict = _worst(verdict, YELLOW)
                reasons.append(
                    f"{len(exhibitions)} exhibitions, fewer than the expected "
                    f"{min_exh} — a venue can look healthy on events while its "
                    f"exhibitions are broken"
                )

    # ── Everything harvested, nothing published ──────────────────────────
    # LMU's Laband Gallery sat green while showing visitors nothing: it
    # harvested events fine, so witness 1 was satisfied, and its zero-streak
    # stayed at zero for the same reason. But every single record was filtered
    # out before publication. That is either correct (all of it was a standing
    # programme) or a bug, and "green" is the wrong answer to both.
    if n_harvested > 0 and n_total == 0:
        verdict = _worst(verdict, YELLOW)
        reasons.append(
            f"scraped {n_harvested} record(s) but published none — everything it "
            f"found was filtered out, so the site shows nothing for this venue"
        )

    # ── Nothing on the site for this venue ───────────────────────────────
    # A venue showing visitors nothing is never "green". Museum of Tolerance
    # sat green while publishing nothing at all, because it landed just under
    # every threshold at once: two silent runs (the alarm needs three), no
    # future dates on its page (so the page comparison declined to judge), and
    # nothing harvested this run (so the "harvested but published none" check
    # did not apply). Every witness declined, and silence read as health.
    #
    # This may well be innocent — a small venue between programmes — so it is
    # yellow rather than red, and the reason says which. But "green" has to
    # mean "we checked and it is working", not "we found no evidence either
    # way". That distinction is the whole point of the report.
    if n_total == 0 and verdict == GREEN:
        verdict = YELLOW
        if dates_on_page == 0:
            reasons.append(
                "nothing on the site for this venue — though its own page shows "
                "no upcoming dates either, so this may simply be a quiet period"
            )
        else:
            reasons.append(
                "nothing on the site for this venue, and no check could tell us why"
            )

    # ── Quality of what we did publish ───────────────────────────────────
    notes = []
    for ev in published:
        notes.extend(ev.get("_quality_notes") or [])
    if notes:
        verdict = _worst(verdict, YELLOW)
        reasons.append(f"{len(notes)} record(s) published with a text problem")

    return {
        "venue_id": venue_id,
        "verdict": verdict,
        "unreachable": unreachable,
        "events": len(events),
        "exhibitions": len(exhibitions),
        "dates_on_page": dates_on_page,
        "zero_streak": streak,
        "reasons": reasons,
        "known_gaps": known_gaps,
    }


# ── The fleet ─────────────────────────────────────────────────────────────

def assess(published: list[dict], health: dict, venues: list[dict],
           expectations: dict, probe: bool = True,
           scraped_ids: list[str] | None = None,
           harvested: dict[str, list] | None = None) -> dict:
    """Build the whole status report.

    `harvested` maps venue_id -> the records the scrapers returned this run,
    before curation. Witness 1 needs it; without it (a --skip-scrape run) that
    witness is skipped rather than guessed at.
    """
    by_venue: dict[str, list[dict]] = {}
    for ev in published:
        by_venue.setdefault(ev.get("venue_id"), []).append(ev)

    venue_meta = {v["id"]: v for v in venues if v.get("id")}
    # Only judge venues we actually tried to scrape this run.
    targets = sorted(set(scraped_ids or by_venue.keys()) & set(venue_meta))

    # Witness 1 needs the harvest to compare against; without it, skip it.
    page_dates: dict[str, int | None] = {}
    probed: set[str] = set()
    if probe and harvested is not None:
        probed = set(targets)
        def _probe(vid):
            return vid, count_future_dates_on_page(venue_meta[vid].get("events_url"))
        with ThreadPoolExecutor(max_workers=8) as pool:
            page_dates = dict(pool.map(_probe, targets))

    venues_report = [
        assess_venue(
            vid,
            produced=(harvested or {}).get(vid, []),
            published=by_venue.get(vid, []),
            health=health.get(vid) or {},
            expectation=expectations.get(vid) or {},
            dates_on_page=page_dates.get(vid),
            unreachable=(vid in probed and page_dates.get(vid) is None),
        )
        for vid in targets
    ]
    venues_report.sort(key=lambda r: (-_RANK[r["verdict"]], r["venue_id"]))

    counts = {RED: 0, YELLOW: 0, GREEN: 0}
    for r in venues_report:
        counts[r["verdict"]] += 1
    unreachable = [r["venue_id"] for r in venues_report if r.get("unreachable")]
    exhibition_gap = [r["venue_id"] for r in venues_report
                      if "exhibitions" in (r.get("known_gaps") or [])]

    # The fleet verdict. One broken venue out of sixty is a yellow day, not a
    # red one; several at once means something systemic.
    if counts[RED] >= 5:
        overall = RED
    elif counts[RED] or counts[YELLOW] >= 8:
        overall = YELLOW
    else:
        overall = GREEN

    blocking = sum(1 for ev in published if quality_report(ev)[0])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": overall,
        "totals": {
            "events": sum(1 for e in published if e.get("event_type") != "exhibition"),
            "exhibitions": sum(1 for e in published if e.get("event_type") == "exhibition"),
            "venues_producing": len([v for v in venues_report if v["events"] or v["exhibitions"]]),
            "venues_checked": len(venues_report),
            "unpublishable_records": blocking,
        },
        "counts": counts,
        "unreachable": unreachable,
        # Reported once, as a number, instead of as a fresh complaint against
        # each venue every day. See evals/WATCHLIST.md for the full story.
        "known_exhibition_gap": exhibition_gap,
        "venues": venues_report,
    }


def record_history(health: dict, results: list[tuple[str, list]], keep: int = 14) -> dict:
    """Append this run's per-venue count to the rolling history used by witness 2."""
    for venue_id, events in results:
        entry = health.setdefault(venue_id, {})
        history = list(entry.get("recent_counts") or [])
        history.append(len(events))
        entry["recent_counts"] = history[-keep:]
    return health
