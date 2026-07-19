"""LLM fallback for events the scrapers couldn't fully parse.

Gated on the ANTHROPIC_API_KEY environment variable (a GitHub Actions secret in
CI) — when absent this module is a silent no-op, so forks keep working with
zero keys.

Only events DROPPED for a missing start date are sent (capped per run). For
each, we fetch the event's own page, hand Claude Haiku the visible text, and
ask for strict JSON: start/end/price/audience. If a valid ISO start comes
back, the event is recovered into the publishable list.
"""
from __future__ import annotations

import json
import os
import re

import requests as _requests
from bs4 import BeautifulSoup

from .http import get
from .dateparse import to_la_iso

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_PER_RUN = 10
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")

PROMPT = """From this event page text, extract when the event happens and what it costs.
Event title: {title}

Page text:
{text}

Reply with ONLY a JSON object, no other words:
{{"start": "<ISO 8601 datetime with -07:00/-08:00 offset, or YYYY-MM-DD if no time is given, or null if the page truly has no date>",
 "end": "<same format or null>",
 "price_text": "<'Free' or '$N' or '$N-$M' or null>",
 "is_free": <true/false/null>,
 "audience": <["family"] and/or ["teen"] or []>}}
Dates are for Los Angeles. Do not invent a time if only a date is shown."""


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _page_text(url: str) -> str:
    resp = get(url)
    if resp is None or not resp.ok:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.find("main") or soup.body or soup
    return main.get_text(" ", strip=True)[:4000]


def _ask(title: str, text: str) -> dict | None:
    try:
        r = _requests.post(
            API_URL,
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": PROMPT.format(title=title, text=text)}],
            },
            timeout=45,
        )
        if r.status_code != 200:
            print(f"  [llm] API {r.status_code}: {r.text[:120]}")
            return None
        content = r.json()["content"][0]["text"].strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(content)
    except Exception as e:
        print(f"  [llm] failed: {type(e).__name__}: {e}")
        return None


def recover(dropped: list[dict]) -> list[dict]:
    """Try to recover no-start-date drops via the LLM. Returns fixed events."""
    if not enabled():
        return []
    candidates = [e for e in dropped if not e.get("start") and e.get("url")][:MAX_PER_RUN]
    recovered = []
    for ev in candidates:
        text = _page_text(ev["url"])
        if len(text) < 80:
            continue
        out = _ask(ev.get("title", ""), text)
        if not out or not out.get("start") or not _ISO.match(str(out["start"])):
            continue
        fixed = dict(ev)
        fixed["start"] = to_la_iso(out["start"])
        fixed["end"] = to_la_iso(out["end"]) if out.get("end") else None
        fixed["all_day"] = "T" not in str(fixed["start"])
        if out.get("price_text") and not fixed.get("price_text"):
            fixed["price_text"] = str(out["price_text"])[:20]
        if out.get("is_free") in (True, False) and fixed.get("is_free") is None:
            fixed["is_free"] = out["is_free"]
        aud = out.get("audience")
        if isinstance(aud, list) and not fixed.get("audience"):
            fixed["audience"] = [a for a in aud if a in ("family", "teen")]
        fixed["source"] = (fixed.get("source") or "") + "+llm"
        recovered.append(fixed)
        print(f"  [llm] recovered: [{ev.get('venue_id')}] {ev.get('title','')[:50]} -> {fixed['start']}")
    return recovered
