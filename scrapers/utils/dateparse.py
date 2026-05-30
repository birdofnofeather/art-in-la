"""Date parsing helpers.

Every venue and every member of the audience is in Los Angeles, so the goal is
simple: an event must display the exact local clock time the venue's own site
shows. Two cases:

* The source gives a real time. If it is tagged with a timezone (some sites
  store times in UTC even though they render them in LA), we express that same
  instant in LA time — i.e. exactly what the venue's page displays. A time with
  no timezone is already LA-local and is kept verbatim (no shift).

* The source gives only a date (it resolves to midnight in its own timezone).
  That is a date-only listing with no published time, so we return a bare
  'YYYY-MM-DD' and never invent a "12:00 AM" — and we use the source's own
  calendar date, with no conversion that could roll it back a day.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from dateutil import parser as du_parser
import pytz

LA = pytz.timezone("America/Los_Angeles")


def to_la_iso(value, all_day: bool = False) -> Optional[str]:
    """Coerce a date/datetime input to an LA-local ISO 8601 string."""
    if value is None or value == "":
        return None

    # Pure date object (no time-of-day) -> all-day date.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = du_parser.parse(str(value))
        except (ValueError, TypeError, OverflowError, du_parser.ParserError):
            return None
    if dt is None:
        return None

    # A value at exactly midnight *in its own timezone* is a date-only listing.
    # Return that calendar date untouched (no conversion → never rolls back a day).
    if all_day or (dt.hour == 0 and dt.minute == 0 and dt.second == 0):
        return dt.date().isoformat()

    # A real time. Naive == already LA-local (keep verbatim); tz-aware == express
    # the same instant in LA so it matches what the venue's site shows.
    if dt.tzinfo is None:
        dt = LA.localize(dt)
    else:
        dt = dt.astimezone(LA)
    return dt.replace(microsecond=0).isoformat()


def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
