"""Group A — are the things we publish actually real?

This is the group that matters most, and until now nothing in the project did
it at all. Every other check in the suite asks "did our code do what our code
does?". These go and look at the venue's own website and ask a different
question: is the event we are showing people actually there?

Three ways a published event can be a lie, in increasing order of harm:

  1. The link is dead. Someone taps the event and lands on a 404.
  2. The event is not on the page any more. It was cancelled or removed and we
     are still advertising it.
  3. The event was never there. Some part of our pipeline invented it — a
     parser reading the wrong element, or (once the AI extraction tier exists)
     a model filling in a plausible-sounding blank.

The third is the one worth building for. On a public calendar people plan trips
around, a confidently fabricated event is a much worse failure than a missing
one, and it is completely invisible from the inside: the record looks perfect,
the count looks healthy, the date parses.

Everything here is sampled, not exhaustive — checking 400 events every run
would hammer venues we depend on. A sample of 25 finds a systemic problem
quickly and a rare one eventually.
"""
from __future__ import annotations

import random
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from bs4 import BeautifulSoup

from ..utils.http import get
from ..utils.text import normalise
from .model import Finding, PASS, FAIL, WARN, SKIP

SAMPLE_SIZE = 25

# Words too common to prove anything about a match.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "is", "are", "as", "this", "that", "new", "art", "los",
    "angeles", "la", "museum", "gallery", "center", "centre", "presents",
}

# How much of a title's distinctive wording must appear on the page.
TITLE_MATCH_FLOOR = 0.6

# Below this share of the sample matching, we have a real problem.
HEALTHY_MATCH_RATE = 0.75
ALARMING_MATCH_RATE = 0.5


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalise(text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _page_text(url: str) -> str | None:
    """The visible words of a page, or None if we could not fetch it."""
    resp = get(url)
    if resp is None or not resp.ok:
        return None
    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return normalise(soup.get_text(" ", strip=True)).lower()


def _date_appears(start: str, page: str) -> bool:
    """Does this event's date appear on the page, written any ordinary way?"""
    try:
        when = datetime.fromisoformat(str(start).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return False
    month_full = when.strftime("%B").lower()
    month_abbr = when.strftime("%b").lower()
    day = str(when.day)
    forms = [
        f"{month_full} {day}", f"{month_abbr} {day}", f"{month_abbr}. {day}",
        f"{day} {month_full}", when.isoformat(),
        f"{when.month}/{when.day}/{when.year}", f"{when.month}/{when.day}",
    ]
    return any(f in page for f in forms)


def _check_one(event: dict) -> dict:
    """Fetch one event's own page and see whether the event is on it."""
    url = event.get("url")
    result = {
        "id": event.get("id"), "venue": event.get("venue_id"),
        "title": event.get("title", "")[:70], "url": url,
        "reachable": False, "title_found": False, "date_found": False,
    }
    if not url:
        return result
    page = _page_text(url)
    if page is None:
        return result
    result["reachable"] = True

    wanted = _tokens(event.get("title", ""))
    if wanted:
        present = {w for w in wanted if w in page}
        result["match_ratio"] = len(present) / len(wanted)
        result["title_found"] = result["match_ratio"] >= TITLE_MATCH_FLOOR
    else:
        result["title_found"] = False

    result["date_found"] = _date_appears(event.get("start"), page)
    return result


def sample_and_verify(events: list[dict], size: int = SAMPLE_SIZE,
                      seed: int | None = None) -> list[dict]:
    """Pick a spread of events across venues and check each against its page."""
    linked = [e for e in events if e.get("url") and e.get("event_type") != "exhibition"]
    if not linked:
        return []

    # Spread the sample across venues rather than letting one big venue
    # (Academy Museum publishes a third of everything) dominate it.
    by_venue: dict[str, list[dict]] = {}
    for ev in linked:
        by_venue.setdefault(ev.get("venue_id"), []).append(ev)

    rng = random.Random(seed)
    picks, venues = [], sorted(by_venue)
    rng.shuffle(venues)
    round_no = 0
    while len(picks) < size and round_no < 10:
        for venue in venues:
            pool = by_venue[venue]
            if round_no < len(pool):
                picks.append(pool[round_no])
                if len(picks) >= size:
                    break
        round_no += 1

    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(_check_one, picks))


def run(events: list[dict], seed: int | None = None) -> list[Finding]:
    checks = sample_and_verify(events, seed=seed)
    if not checks:
        return [Finding(
            "A0", "Could we sample any events to verify?", SKIP,
            "No published events carry a link, so nothing could be checked "
            "against its source page.", independent=True,
        )]

    reachable = [c for c in checks if c["reachable"]]
    dead = [c for c in checks if not c["reachable"]]
    titled = [c for c in reachable if c["title_found"]]
    dated = [c for c in reachable if c["date_found"]]

    findings: list[Finding] = []

    # ── A1: are we inventing events? ─────────────────────────────────────
    rate = len(titled) / len(reachable) if reachable else 0
    missing = [c for c in reachable if not c["title_found"]]
    if not reachable:
        verdict, detail = SKIP, "None of the sampled pages could be fetched."
    elif rate >= HEALTHY_MATCH_RATE:
        verdict = PASS
        detail = (f"{len(titled)} of {len(reachable)} sampled events were found "
                  f"on the venue's own page. Nothing looks invented.")
    elif rate >= ALARMING_MATCH_RATE:
        verdict = WARN
        detail = (f"Only {len(titled)} of {len(reachable)} sampled events could be "
                  f"found on their own page. Some of this is normal — venues "
                  f"restyle titles — but it is worth reading the misses below.")
    else:
        verdict = FAIL
        detail = (f"Only {len(titled)} of {len(reachable)} sampled events could be "
                  f"found on the page they link to. Either we are publishing "
                  f"events that do not exist, or we are linking them to the "
                  f"wrong pages. Both mislead people.")
    findings.append(Finding(
        "A1", "Do the events we publish actually appear on the venue's own page?",
        verdict, detail,
        evidence=[f"[{c['venue']}] {c['title']} -> {c['url']}" for c in missing[:6]],
        independent=True,
        numbers={"sampled": len(checks), "reachable": len(reachable),
                 "title_found": len(titled), "match_rate": round(rate, 3)},
    ))

    # ── A2: do the dates match what the venue says? ──────────────────────
    date_rate = len(dated) / len(reachable) if reachable else 0
    wrong_date = [c for c in reachable if c["title_found"] and not c["date_found"]]
    findings.append(Finding(
        "A2", "Does each event's date actually appear on the venue's page?",
        PASS if date_rate >= 0.5 else WARN,
        (f"{len(dated)} of {len(reachable)} sampled events had their date visible "
         f"on the page. A low score here is often innocent — many venues put the "
         f"date in an image or a booking widget we cannot read — so this is "
         f"tracked as a trend rather than treated as a failure."),
        evidence=[f"[{c['venue']}] {c['title']}" for c in wrong_date[:5]],
        independent=True,
        numbers={"date_found": len(dated), "date_rate": round(date_rate, 3)},
    ))

    # ── A3: dead links ───────────────────────────────────────────────────
    dead_rate = len(dead) / len(checks)
    findings.append(Finding(
        "A3", "Do the links we publish still work?",
        PASS if dead_rate <= 0.1 else (WARN if dead_rate <= 0.25 else FAIL),
        (f"{len(dead)} of {len(checks)} sampled links could not be opened. "
         f"Some venues block automated requests while working fine in a browser, "
         f"so a handful is expected; a lot means we are sending people to pages "
         f"that no longer exist."),
        evidence=[f"[{c['venue']}] {c['url']}" for c in dead[:6]],
        independent=True,
        numbers={"dead": len(dead), "dead_rate": round(dead_rate, 3)},
    ))

    return findings
