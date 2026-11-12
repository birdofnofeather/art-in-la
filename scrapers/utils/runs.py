"""Collapse a production's many performances into one "run" listing.

Performing-arts venues list every performance of a production separately —
Pasadena Playhouse publishes "Passing Strange" fourteen times, plus variants
like "Passing Strange WINE WEDNESDAY" and "Passing Strange CLOSING"; East West
Players adds "(Preview Performance)", "(Opening Night)", "(Masked Matinee)".

Left alone, the recurring-programme filter sees fourteen same-title records on
a regular rhythm and drops the production entirely while the marketing
variants survive — the exact opposite of what a visitor needs. So for venues
whose discipline is "performing", every performance of one production becomes
ONE record spanning its first to last date, noting the number of performances.
Like an exhibition, a run is a date range, so the recurring filter and the
"one-off spanning > 4 days" hygiene rule both exempt it (`_run: True`).
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .event_id import event_id
from .recurring import is_recurring_by_keyword

# Only trailing qualifiers that describe a PERFORMANCE are stripped — never
# a parenthesis that is part of the title ("SOFT MAGICAL TOFU BOY(S)").
_PAREN_TAIL = re.compile(
    r"\s*[\(\[][^\)\]]{0,40}\b(?:preview|opening|closing|matinee|performance|"
    r"festival|asl|captioned|relaxed|sensory|talkback|sold out|encore|"
    r"night|evening|gala|access|livestream|in person|reading)\b[^\)\]]{0,40}[\)\]]\s*$",
    re.I,
)
_AT_PLACE = re.compile(
    r"\s+(?:at|@)\s+(?:the\s+)?[A-Z][\w'’.\- ]{0,60}"
    r"(?:Library|Theat(?:er|re)|Hall|Cent(?:er|re)|Park|Museum|Stage|Room|Branch|Plaza|Bowl)\b.*$"
)
_SEP_TAIL = re.compile(r"[\s:\-–—|,]+$")


RUN_GAP_DAYS = 21
# Theaters go dark Mon–Wed, so a Thu–Sun run has gaps of up to 4 days;
# a weekly class (7) must never qualify.
RUN_MAX_MEDIAN_GAP = 4


def _base(title: str) -> str:
    t = (title or "").strip()
    for _ in range(2):
        t = _PAREN_TAIL.sub("", t)
    t = _AT_PLACE.sub("", t)
    return _SEP_TAIL.sub("", t).strip()


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _day(raw) -> date | None:
    try:
        return date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None


def _fmt(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def collapse_runs(events: list[dict], performing_ids: set[str]) -> list[dict]:
    from .rules import load
    # A venue whose series are deliberately DROPPED (rules.yaml venue_overrides,
    # e.g. Pieter's weekly classes) never has them bundled into runs.
    overrides = load().recurring_venue_overrides
    performing_ids = {v for v in performing_ids if overrides.get(v) != "drop"}
    out, by_venue = [], defaultdict(list)
    for ev in events:
        if (ev.get("venue_id") in performing_ids and ev.get("event_type") != "exhibition"
                and not ev.get("_run") and _day(ev.get("start"))):
            by_venue[ev["venue_id"]].append(ev)
        else:
            out.append(ev)

    for venue_id, evs in by_venue.items():
        # 1. group by base title
        groups: dict[str, list[dict]] = defaultdict(list)
        display: dict[str, str] = {}
        for ev in evs:
            b = _base(ev.get("title") or "")
            k = _key(b)
            groups[k].append(ev)
            if k not in display or len(b) < len(display[k]):
                display[k] = b
        # 2. fold "Base SUFFIX" variants into "Base" when the suffix is a
        #    shouted qualifier ("WINE WEDNESDAY", "CLOSING", "ACCESS PERFORMANCE").
        for k in sorted(groups, key=len, reverse=True):
            for parent in sorted(groups, key=len):
                if parent == k or len(parent) < 4 or not k.startswith(parent + " "):
                    continue
                suffix = display[k][len(display[parent]):].strip()
                letters = re.sub(r"[^A-Za-z]", "", suffix)
                if letters and letters.isupper():
                    groups[parent].extend(groups.pop(k))
                    break
        # 2b. split each group where performances are > RUN_GAP_DAYS apart —
        #     an annual Nutcracker is a new run each December, not one
        #     year-long record spanning two seasons.
        split: dict[str, list[dict]] = {}
        for k, members in groups.items():
            members = sorted(members, key=lambda m: str(m.get("start")))
            chunk, last, n = [], None, 0
            for m in members:
                d = _day(m.get("start"))
                if last and d and (d - last).days > RUN_GAP_DAYS:
                    split[f"{k}#{n}"] = chunk; chunk, n = [], n + 1
                chunk.append(m); last = d or last
            split[f"{k}#{n}"] = chunk
        groups = split
        display = {gk: display[gk.rsplit("#", 1)[0]] for gk in groups}

        # 3. one record per production with 2+ dates — but only when the dates
        #    look like a RUN (performances clustered a few days apart). A
        #    weekly class or monthly series is a standing programme: leave it
        #    to the recurring filter, which hides it. Likewise anything whose
        #    name marks it as a standing programme.
        for k, members in groups.items():
            days = sorted({d for m in members for d in (_day(m.get("start")), _day(m.get("end"))) if d})
            starts = sorted({_day(m.get("start")) for m in members})
            gaps = sorted((b - a).days for a, b in zip(starts, starts[1:]))
            median_gap = gaps[len(gaps) // 2] if gaps else 99
            if len(members) == 1 and not is_recurring_by_keyword(display[k]):
                # One record already spanning several days is a production run
                # as the venue itself published it ("The Music Man, Nov 4 – Dec 20").
                m = dict(members[0])
                first, last = _day(m.get("start")), _day(m.get("end"))
                if first and last and (last - first).days >= 2:
                    m.update({"_run": True,
                              "recurrence_note": f"Runs {_fmt(first)} – {_fmt(last)}"})
                    if m.get("event_type") in ("opening", "closing", "screening", "workshop", "fair", "other"):
                        m["event_type"] = "performance"
                        m["event_types"] = ["performance"]
                out.append(m)
                continue
            if (len(starts) < 2 or median_gap > RUN_MAX_MEDIAN_GAP
                    or is_recurring_by_keyword(display[k])):
                out.extend(members)
                continue
            plain = [m for m in members if _key(m.get("title") or "") == k.rsplit("#", 1)[0]]
            best = dict(max(plain or members,
                            key=lambda m: sum(1 for f in ("description", "url", "image") if m.get(f))))
            first, last = days[0], days[-1]
            n = len({(m.get("start") or "") for m in members})
            # A touring production ("… at Westwood Branch Library") keeps its
            # list of places in the description, so folding loses nothing.
            places = []
            for m in sorted(members, key=lambda m: str(m.get("start"))):
                hit = _AT_PLACE.search(m.get("title") or "")
                if hit:
                    place = re.sub(r"^\s+(?:at|@)\s+(?:the\s+)?", "", hit.group(0)).strip()
                    if place and place not in places:
                        places.append(place)
            best.update({
                "id": event_id(venue_id, first.isoformat(), display[k]),
                "title": display[k],
                "start": first.isoformat(),
                "end": last.isoformat(),
                "all_day": True,
                "_run": True,
                "run_count": n,
                # Each performance day, so the site's "Today"/"This weekend"
                # include a run only on days it actually plays.
                "run_dates": sorted({str(m.get("start"))[:10] for m in members if m.get("start")}),
                "recurrence_note": f"{n} performances · {_fmt(first)} – {_fmt(last)}",
            })
            if places:
                best["description"] = ("At: " + "; ".join(places) + ". " + (best.get("description") or "")).strip()
            if best.get("event_type") in ("opening", "closing", "screening", "workshop", "fair", "other"):
                best["event_type"] = "performance"
                best["event_types"] = ["performance"]
            if any(m.get("is_free") is True for m in members) and best.get("is_free") is None:
                best["is_free"] = True
            out.append(best)
    return out
