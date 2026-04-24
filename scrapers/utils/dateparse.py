"""Date parsing helpers. All times normalize to America/Los_Angeles for LA venues."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as du_parser
import pytz

LA = pytz.timezone("America/Los_Angeles")


def to_la_iso(value, all_day: bool = False) -> Optional[str]:
    """Coerce any reasonable date/datetime input to an ISO8601 string in LA time."""
    if value is None or value == "":
        return None
    dt: Optional[datetime] = None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = du_parser.parse(str(value))
        except (ValueError, TypeError, du_parser.ParserError):
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = LA.localize(dt)
    else:
        dt = dt.astimezone(LA)
    if all_day:
        return dt.date().isoformat()
    return dt.isoformat()


def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
