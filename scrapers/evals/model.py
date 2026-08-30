"""What a single check produces.

A note on the most important field here, `independent`.

It is easy to write a check that proves nothing. If a check calls our own code
and then asserts that our own code returned what our own code returns, it will
pass forever, including on the day everything breaks. Half the checks in this
suite are that kind — they are still useful, because they catch a change from
one day to the next — but they cannot tell us whether we were ever right.

A check marked `independent=True` compares us against something outside our own
system: the venue's own website, or a copy of that website saved before the
code changed. Those are the only checks that can catch us being confidently
wrong, and the summary reports them separately for that reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

PASS = "pass"        # working as intended
FAIL = "fail"        # genuinely broken; needs a fix
WARN = "warn"        # suspicious; worth watching, may be fine
SKIP = "skip"        # could not run (no data yet, no network)

# For the headline verdict, a check that could not run is NOT worse than one
# that passed. An early version ranked it above PASS, so a clean run where a
# single check had no data to work with was headlined "SKIP" — which reads like
# something went wrong and buries the fact that everything else was fine.
_RANK = {SKIP: 0, PASS: 1, WARN: 2, FAIL: 3}


@dataclass
class Finding:
    id: str                       # short stable id, e.g. "A1"
    question: str                 # the plain-English question this answers
    verdict: str                  # pass / fail / warn / skip
    detail: str                   # plain-English result, readable on its own
    evidence: list[str] = field(default_factory=list)   # concrete examples
    independent: bool = False     # checked against the outside world?
    numbers: dict = field(default_factory=dict)         # tracked across runs

    def to_dict(self) -> dict:
        return asdict(self)


def worst(findings: list[Finding]) -> str:
    """The headline verdict: the most serious thing that actually happened.

    Checks that could not run are reported in the counts but never become the
    headline — "could not check X" is not the same news as "X is broken".
    """
    ran = [f.verdict for f in findings if f.verdict != SKIP]
    if not ran:
        return SKIP
    return max(ran, key=lambda v: _RANK.get(v, 0))


def counts(findings: list[Finding]) -> dict:
    out = {PASS: 0, FAIL: 0, WARN: 0, SKIP: 0}
    for f in findings:
        out[f.verdict] = out.get(f.verdict, 0) + 1
    return out
