"""Quality gate for ONE venue's live scrape — used by the repair workflow.

`python -m scrapers.verify_venue <venue_id>` scrapes the venue for real
(parser only: dry runs never call the LLM), applies the full curation rules,
and exits 0 only if what would be PUBLISHED looks right:

  * at least one record survives curation (not merely "something parsed");
  * every published title is a real title — not navigation, a button label,
    a bare date, or empty;
  * every date is plausible (not ended, not years ahead);
  * curation did not have to throw away most of the harvest (a parser reading
    the wrong part of the page produces mostly junk that gets dropped).

Prints a short report either way. Exit 1 = not good enough to publish.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

os.environ.setdefault("ART_IN_LA_DRY_RUN", "1")


def check(venue_id: str) -> tuple[bool, list[str]]:
    from . import storage
    from .classify import derive
    from .registry import SCRAPERS
    from .utils.generic_listing import _JUNK_TITLE, _is_only_date

    rows = {v["id"]: v for v in storage.load_venues()}
    cls = next((c for c in SCRAPERS if c.venue_id == venue_id), None)
    if cls is None or venue_id not in rows:
        return False, [f"unknown venue {venue_id}"]
    inst = cls()
    inst.venue_name = rows[venue_id].get("name", venue_id)
    if not inst.exhibitions_url and rows[venue_id].get("exhibitions_url"):
        inst.exhibitions_url = rows[venue_id]["exhibitions_url"]
    harvested = inst.run()
    result = derive(harvested)
    published = [e for e in result.upcoming if e.get("venue_id") == venue_id]
    problems, notes = [], [f"harvested {len(harvested)}, published {len(published)}"]
    if not published:
        problems.append("nothing survives curation")
    today = date.today()
    for e in published:
        t = (e.get("title") or "").strip()
        if len(t) < 3 or len(t) > 200 or _JUNK_TITLE.match(t) or _is_only_date(t):
            problems.append(f"junk title: {t!r}")
        s = str(e.get("start") or "")[:10]
        end = str(e.get("end") or e.get("start") or "")[:10]
        try:
            if end and date.fromisoformat(end) < today - timedelta(days=1):
                problems.append(f"already ended: {t!r} {end}")
            if s and date.fromisoformat(s) > today + timedelta(days=550):
                problems.append(f"implausibly far ahead: {t!r} {s}")
        except ValueError:
            problems.append(f"bad date on {t!r}: {s}")
    dropped = len(result.dropped_hygiene)
    if harvested and dropped > max(3, 0.5 * len(harvested)):
        problems.append(f"curation dropped {dropped} of {len(harvested)} — parser likely reading the wrong content")
    for e in published[:8]:
        notes.append(f"  {str(e.get('start'))[:16]}  {e.get('title','')[:70]}")
    return not problems, notes + problems


if __name__ == "__main__":
    ok, lines = check(sys.argv[1])
    print("\n".join(lines))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
