"""Whole-fleet safety checks, run immediately before publishing.

Per-venue monitoring catches one venue breaking. These catch the more dangerous
case: something in the SHARED machinery — the date handling, the exhibition
rule, the recurring filter, a rules.yaml edit — quietly damaging every venue at
once. A per-venue check cannot see that, because every venue looks equally
wrong and there is nothing to compare against.

So this compares the run against the last published state and refuses to
publish if the change is too large to be real. When it refuses, yesterday's
data stays on the site and the failure is reported. Losing a day of freshness
is a much smaller harm than replacing a working calendar with a broken one, and
this is what makes unattended operation safe.

Each check returns a plain-English reason, because these fire on days when
nobody is watching and the message is the whole diagnosis.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Publishing is blocked if the event count moves by more than this against the
# previous run. Real daily movement is a few percent; a third is a catastrophe.
MAX_TOTAL_SWING = 0.35

# ...unless we are starting from very little, where percentages are meaningless.
SMALL_RUN = 25

# Publishing is blocked if this many venues that were producing go to zero at
# once. One venue breaking is normal. Ten at once is our bug, not theirs.
MAX_VENUES_LOST = 6


@dataclass
class FleetCheck:
    ok: bool = True
    blocking: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def block(self, reason: str) -> None:
        self.ok = False
        self.blocking.append(reason)

    def warn(self, reason: str) -> None:
        self.warnings.append(reason)

    def summary(self) -> str:
        if self.ok and not self.warnings:
            return "All fleet checks passed."
        lines = []
        if self.blocking:
            lines.append("PUBLISHING BLOCKED:")
            lines += [f"  - {r}" for r in self.blocking]
        if self.warnings:
            lines.append("Warnings:")
            lines += [f"  - {r}" for r in self.warnings]
        return "\n".join(lines)


def _by_venue(events: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for ev in events:
        out[ev.get("venue_id") or "?"] = out.get(ev.get("venue_id") or "?", 0) + 1
    return out


def check(new_events: list[dict], previous_events: list[dict],
          new_archive: list[dict], previous_archive: list[dict]) -> FleetCheck:
    """Compare a proposed publish against the last one."""
    result = FleetCheck()

    # ── Nothing at all ───────────────────────────────────────────────────
    if not new_events:
        result.block("the run produced no events at all")
        return result

    # ── Duplicate ids ────────────────────────────────────────────────────
    ids = [e.get("id") for e in new_events if e.get("id")]
    if len(ids) != len(set(ids)):
        result.block(f"{len(ids) - len(set(ids))} duplicate event ids — "
                     f"the same event would appear twice on the site")
    if len(ids) != len(new_events):
        result.block(f"{len(new_events) - len(ids)} events have no id")

    # ── Total swing ──────────────────────────────────────────────────────
    before, after = len(previous_events), len(new_events)
    if before >= SMALL_RUN:
        swing = (after - before) / before
        if swing <= -MAX_TOTAL_SWING:
            result.block(
                f"event count fell from {before} to {after} "
                f"({swing:+.0%}) — too large to be a real day's change"
            )
        elif swing >= MAX_TOTAL_SWING:
            result.warn(
                f"event count rose from {before} to {after} ({swing:+.0%}) — "
                f"worth a look, but a rise is not dangerous so publishing continues"
            )

    # ── Venues going dark together ───────────────────────────────────────
    was, now = _by_venue(previous_events), _by_venue(new_events)
    lost = sorted(v for v, n in was.items() if n > 0 and now.get(v, 0) == 0)
    if len(lost) > MAX_VENUES_LOST:
        result.block(
            f"{len(lost)} venues that were producing returned nothing at once "
            f"({', '.join(lost[:6])}…) — that points at our pipeline, not their websites"
        )
    elif lost:
        result.warn(f"{len(lost)} venue(s) went quiet: {', '.join(lost)}")

    # ── The archive must never shrink ────────────────────────────────────
    # A venue's website stops listing an event once it has happened, so a lost
    # archive record can never be recovered. This is the check that would have
    # caught the merge bug that took the archive from 757 records to 203.
    if len(new_archive) < len(previous_archive) * 0.9 and len(previous_archive) > 50:
        result.block(
            f"the archive shrank from {len(previous_archive)} to {len(new_archive)} "
            f"records — past events cannot be re-scraped, so this is unrecoverable"
        )

    # ── Every event must be placeable and clickable ──────────────────────
    undated = [e for e in new_events
               if e.get("event_type") != "exhibition" and not e.get("start")]
    if undated:
        result.block(f"{len(undated)} non-exhibition events have no start date")

    return result
