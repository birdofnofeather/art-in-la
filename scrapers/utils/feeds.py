"""Generate subscribable .ics calendar feeds.

Writes public/data/feeds/{all,free,family}.ics so a user can add the whole
calendar to Google/Apple Calendar once and never visit the site again — the
lowest-maintenance form of the project's "runs itself" promise.

Timezone rules mirror the frontend (src/lib/calendar.js): a real datetime is
emitted as a UTC timestamp; a date-only listing is emitted as a VALUE=DATE.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytz

LA = pytz.timezone("America/Los_Angeles")


def _esc(text) -> str:
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """RFC 5545 line folding at 74 octets."""
    if len(line.encode("utf-8")) <= 74:
        return line
    out, cur = [], ""
    for ch in line:
        if len((cur + ch).encode("utf-8")) > 74:
            out.append(cur)
            cur = " " + ch
        else:
            cur += ch
    out.append(cur)
    return "\r\n".join(out)


def _utc_stamp(raw) -> str | None:
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = LA.localize(dt)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _date_value(raw) -> str:
    return str(raw)[:10].replace("-", "")


def _is_timed(ev) -> bool:
    return "T" in str(ev.get("start") or "") and not ev.get("all_day")


def build_ics(events, venues_by_id, calname: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Art in LA//Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(calname)}",
        "X-WR-TIMEZONE:America/Los_Angeles",
    ]
    for ev in events:
        start = ev.get("start")
        if not start:
            continue
        venue = venues_by_id.get(ev.get("venue_id")) or {}
        location = ev.get("location_override") or venue.get("address") or venue.get("name") or ""
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev.get('id')}@art-in-la")
        lines.append(f"DTSTAMP:{now}")
        if _is_timed(ev):
            s = _utc_stamp(start)
            if not s:
                lines.pop()  # remove DTSTAMP; abandon this VEVENT cleanly
                lines.pop()  # remove BEGIN:VEVENT
                continue
            lines.append(f"DTSTART:{s}")
            end = ev.get("end")
            if end and "T" in str(end):
                e = _utc_stamp(end)
                if e:
                    lines.append(f"DTEND:{e}")
        else:
            lines.append(f"DTSTART;VALUE=DATE:{_date_value(start)}")
            end = ev.get("end")
            if end:
                lines.append(f"DTEND;VALUE=DATE:{_date_value(end)}")
        lines.append(_fold(f"SUMMARY:{_esc(ev.get('title'))}"))
        if location:
            lines.append(_fold(f"LOCATION:{_esc(location)}"))
        if ev.get("url"):
            lines.append(_fold(f"URL:{ev.get('url')}"))
        desc = ev.get("description")
        if desc:
            lines.append(_fold(f"DESCRIPTION:{_esc(desc[:500])}"))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
