"""Pre-publish hygiene gate — every rule comes from scrapers/rules.yaml.

Runs on the upcoming-events list right before it is written, so undated ghosts,
stale records and corrupted text never reach the site. Every drop is recorded
via skip_warn() so it surfaces in warnings.json and on the status page.

Two kinds of check:

  STRUCTURAL — can this event be placed on a calendar at all? (no start date,
  already finished, dates in the far future). These drop the record.

  QUALITY — is what we're about to publish actually clean? (corrupted accents,
  leftover HTML, placeholder titles, missing required fields). These are the
  checks that were missing when six Getty events went live reading "espaÃ±ol".
  A quality failure is repaired where it safely can be, and dropped where it
  cannot.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from .rules import load
from .text import normalise, looks_mojibaked
from .warn import skip_warn


def _parse(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_exhibition(ev: dict) -> bool:
    return (ev.get("event_type") == "exhibition") or (
        "exhibition" in (ev.get("event_types") or [])
    )


def quality_report(ev: dict) -> tuple[list[str], list[str]]:
    """Return (blocking, reportable) quality problems for one event.

    BLOCKING problems mean the event is not published — the text is unusable.
    REPORTABLE problems mean it IS published but the status page mentions it:
    a real event with one unreconstructable accent is still worth showing, and
    losing it would be a worse outcome than displaying it imperfectly.
    """
    rules = load()
    blocking, reportable = [], []

    for fieldname in rules.required_fields:
        if not ev.get(fieldname):
            blocking.append(f"missing required field '{fieldname}'")

    title = ev.get("title") or ""
    if len(title.strip()) < rules.min_title_length:
        blocking.append("title too short to be a real listing")

    haystack = f"{title}\n{ev.get('description') or ''}"
    for forbidden in rules.forbid_in_text:
        if forbidden.pattern.search(haystack):
            bucket = blocking if forbidden.severity == "drop" else reportable
            bucket.append(f"{forbidden.id}: {forbidden.says}")

    url = ev.get("url")
    if url and not str(url).startswith(("http://", "https://")):
        blocking.append("link is not a usable web address")

    return blocking, reportable


def quality_issues(ev: dict) -> list[str]:
    """Only the problems that stop an event being published."""
    return quality_report(ev)[0]


def validate(events, now=None):
    """Return (kept, dropped)."""
    rules = load()
    now = now or datetime.now(timezone.utc)
    past_cutoff = now - timedelta(days=rules.max_days_in_past)
    future_cutoff = now + timedelta(days=rules.max_days_in_future)
    kept, dropped = [], []

    def _drop(ev, reason):
        dropped.append(ev)
        skip_warn(ev.get("venue_id", "?"), ev.get("title", ""), f"dropped ({reason})")

    for ev in events:
        is_exh = _is_exhibition(ev)
        start = _parse(ev.get("start"))
        end = _parse(ev.get("end"))

        # ── Structural ───────────────────────────────────────────────────
        if rules.require_start_unless_exhibition and not is_exh and start is None:
            _drop(ev, "no start date")
            continue

        # A "one-off" spanning more than a few days is a standing programme
        # ("Guided Tours  May 28 - Jul 23"), not something to put on a calendar.
        if not is_exh and start is not None and end is not None:
            if (end - start) > timedelta(days=4):
                _drop(ev, "multi-week range, not a one-off event")
                continue

        # An exhibition with no dates at all can't be placed on a timeline and
        # never reaches the (dates-required) Exhibitions tab, so it is clutter.
        # It re-enters automatically if the scraper later finds dates.
        if is_exh and start is None and end is None:
            _drop(ev, "undated exhibition")
            continue

        finish = end or start
        if finish is not None and finish < past_cutoff:
            _drop(ev, "date range already ended")
            continue
        if start is not None and start > future_cutoff:
            _drop(ev, "start date implausibly far in the future")
            continue

        # ── Quality ──────────────────────────────────────────────────────
        # Corrupted text is repairable, so repair it rather than losing a real
        # event. Anything still failing after the repair is dropped: publishing
        # visible garbage is worse than publishing nothing.
        if looks_mojibaked(ev.get("title") or "") or looks_mojibaked(ev.get("description") or ""):
            ev = dict(ev)
            ev["title"] = normalise(ev.get("title") or "")
            ev["description"] = normalise(ev.get("description") or "")

        blocking, reportable = quality_report(ev)
        if blocking:
            _drop(ev, "quality: " + "; ".join(blocking[:2]))
            continue
        if reportable:
            # Published, but the problem is recorded so it shows up on the
            # status page instead of rotting silently.
            ev = dict(ev)
            ev["_quality_notes"] = reportable

        kept.append(ev)

    return kept, dropped
