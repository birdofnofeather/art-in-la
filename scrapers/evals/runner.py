#!/usr/bin/env python3
"""Run every check and write the results to the logbook.

    python -m scrapers.evals              # run everything, write the log
    python -m scrapers.evals --offline    # skip checks that need the internet
    python -m scrapers.evals --no-write   # print the report, change nothing

Two files are kept, both in evals/:

  LOGBOOK.md    a running diary in plain English, newest entry first. This is
                the thing to read.
  history.json  the same results as numbers, so each run can compare itself
                against the previous one and notice slow bleeding that no
                single day's snapshot would show.

Exit code is 1 if any check failed, so a scheduled run can tell without
reading the text.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from .. import storage
from . import faults, integrity, selftest, truth
from .model import Finding, counts, worst, FAIL, PASS, SKIP, WARN

LOG_DIR = storage.ROOT / "evals"
LOGBOOK = LOG_DIR / "LOGBOOK.md"
HISTORY = LOG_DIR / "history.json"

_ICON = {PASS: "PASS", FAIL: "FAIL", WARN: "WARN", SKIP: "----"}


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return []


def collect(offline: bool = False, seed: int | None = None) -> tuple[list[Finding], dict]:
    events = storage.load_events()
    archive = storage.load_archive()
    raw = storage.load_raw()
    venues = storage.load_venues()
    status = storage.load_json(storage.STATUS_FILE, {})
    expectations = storage.load_expectations()

    history = load_history()
    previous = history[-1].get("snapshot") if history else None

    findings: list[Finding] = []

    # A — verification against the venues' own websites (needs the internet)
    if offline:
        findings.append(Finding(
            "A0", "Do our events appear on the venues' own pages?", SKIP,
            "Skipped: this run was told not to use the internet.", independent=True))
    else:
        findings += truth.run(events, seed=seed)

    # B — what changed since last time
    findings += integrity.drift(events, archive, previous)

    # C — is the safety equipment armed (no internet needed)
    findings += faults.run()

    # D — is the monitoring honest
    findings += integrity.monitoring(status, events, expectations)

    # E — is the published data well formed
    findings += integrity.quality(events, venues)

    # F — is the machinery running
    findings += integrity.pipeline(events, raw, status)

    # G — can these checks detect a problem at all? Read this one first: if it
    # fails, every other "pass" above is unreliable.
    findings += selftest.run(events, venues, offline=offline)

    return findings, integrity.snapshot(events, archive)


def render_report(findings: list[Finding], when: str) -> str:
    tally = counts(findings)
    overall = worst(findings)
    independent = [f for f in findings if f.independent]

    lines = [
        f"## {when[:10]} — {overall.upper()}",
        "",
        f"{tally[PASS]} passed, {tally[FAIL]} failed, {tally[WARN]} need watching, "
        f"{tally[SKIP]} could not run.",
        "",
    ]

    failures = [f for f in findings if f.verdict == FAIL]
    warnings = [f for f in findings if f.verdict == WARN]

    if failures:
        lines += ["### What is broken", ""]
        for f in failures:
            lines += [f"**{f.id} — {f.question}**", "", f.detail, ""]
            lines += [f"- {e}" for e in f.evidence[:6]] + [""] if f.evidence else [""]
    else:
        lines += ["### Nothing is broken", "",
                  "Every check that can fail, passed.", ""]

    if warnings:
        lines += ["### Worth watching", ""]
        for f in warnings:
            lines += [f"- **{f.id}** {f.question} — {f.detail}"]
            lines += [f"    - {e}" for e in f.evidence[:3]]
        lines += [""]

    ind_fail = [f for f in independent if f.verdict in (FAIL, WARN)]
    lines += [
        "### Checked against the outside world",
        "",
        f"{len(independent)} of these checks compared us against the venues' own "
        f"websites rather than against our own code. "
        + ("They all passed." if not ind_fail
           else f"{len(ind_fail)} of them found a problem — those are listed above."),
        "",
        "### Every check",
        "",
        "| | Check | Result |",
        "|---|---|---|",
    ]
    for f in findings:
        mark = "🌐" if f.independent else ""
        lines.append(f"| `{f.id}` {mark} | {f.question} | **{_ICON[f.verdict]}** |")
    lines += ["", "---", ""]
    return "\n".join(lines)


def write_log(findings: list[Finding], snapshot: dict, notes: str = "") -> None:
    when = datetime.now(timezone.utc).isoformat()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    history.append({
        "when": when,
        "verdict": worst(findings),
        "counts": counts(findings),
        "findings": [f.to_dict() for f in findings],
        "snapshot": snapshot,
        "notes": notes,
    })
    HISTORY.write_text(json.dumps(history[-40:], indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    header = (
        "# Eval logbook\n"
        "\n"
        "What this is: every few days the whole system is checked against a fixed\n"
        "set of questions, and the answers are written here, newest first. It\n"
        "exists so that a problem which appears slowly — a venue quietly losing\n"
        "half its events each week — becomes visible, which no single day's\n"
        "snapshot can do.\n"
        "\n"
        "The checks marked 🌐 compare us against the venues' own websites. Those\n"
        "are the only ones that can catch us being confidently wrong; the rest\n"
        "compare our code against itself and can only catch a change.\n"
        "\n"
        "Run it yourself with `python -m scrapers.evals`.\n"
        "\n"
        "---\n"
        "\n"
    )
    entry = render_report(findings, when)
    if notes:
        entry += f"### Notes from this run\n\n{notes}\n\n---\n\n"

    existing = LOGBOOK.read_text(encoding="utf-8") if LOGBOOK.exists() else ""
    body = existing.split("---\n\n", 1)[1] if "---\n\n" in existing else ""
    LOGBOOK.write_text(header + entry + body, encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="Skip the checks that fetch venue websites.")
    parser.add_argument("--no-write", action="store_true",
                        help="Print the report without touching the logbook.")
    parser.add_argument("--notes", default="",
                        help="A line to record alongside this run.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Fix the sampling so a run can be repeated exactly.")
    args = parser.parse_args(argv)

    findings, snap = collect(offline=args.offline, seed=args.seed)
    when = datetime.now(timezone.utc).isoformat()

    print(render_report(findings, when))
    print("\nDetail for every check\n" + "=" * 60)
    for f in findings:
        print(f"\n[{_ICON[f.verdict]}] {f.id} — {f.question}")
        print(f"    {f.detail}")
        if f.numbers:
            print(f"    numbers: {f.numbers}")
        for e in f.evidence[:6]:
            print(f"      - {e}")

    if not args.no_write:
        write_log(findings, snap, notes=args.notes)
        print(f"\nWritten to {LOGBOOK.relative_to(storage.ROOT)} "
              f"and {HISTORY.relative_to(storage.ROOT)}")

    return 1 if any(f.verdict == FAIL for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
