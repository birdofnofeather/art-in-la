"""Getty Calendar scraper.

Getty's calendar (https://www.getty.edu/calendar/) is a client-side Nuxt/Vue app.
The event data is in a JSONP payload file served at:

    https://www.getty.edu/_nuxt/static/{build_hash}/calendar/payload.js

Strategy:
  1. Fetch the /calendar/ HTML to extract the current build hash.
  2. Fetch the payload.js file.
  3. Execute it with Node.js (subprocess) to get structured JSON.
  4. Parse events (talks/films/performances/etc.), tours, and exhibitions.

Node.js >= 18 must be available on the scraping host.  GitHub Actions
ubuntu-latest always ships Node.js, so CI is fine.  Locally: `node -v` to check.

Events are produced for both Getty Center (venue_id="getty_center") and
Getty Villa (venue_id="getty_villa") based on the `location` field.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

# Getty category slugs -> our event_type vocabulary
_CATEGORY_MAP = {
    "talks": "lecture",
    "conferences": "lecture",
    "performances": "performance",
    "films": "screening",
    "art-making": "workshop",
    "family": "workshop",
    "demonstrations": "workshop",
    "tours": "tour",
    "exhibitions": "exhibition",
    "special-events": "other",
    "food": "other",
}

# Location slug -> human-readable
_LOCATION_MAP = {
    "getty-center": "Getty Center",
    "getty-villa": "Getty Villa",
    "online": "Online",
}


def _infer_venue(location_list: list) -> str:
    """Return 'getty_villa' if event is exclusively at Villa, else 'getty_center'."""
    locs = set(location_list or [])
    if locs == {"getty-villa"}:
        return "getty_villa"
    return "getty_center"


def _location_label(location_list: list) -> str | None:
    labels = [_LOCATION_MAP.get(s, s) for s in (location_list or [])]
    return " & ".join(labels) if labels else None


def _category_to_type(categories: list, title: str = "", desc: str = "") -> str:
    for cat in (categories or []):
        mapped = _CATEGORY_MAP.get(cat)
        if mapped:
            return mapped
    return infer_type(title, desc)


def _extract_events_node(payload_js: str) -> list[dict]:
    """Execute Getty's JSONP payload.js via Node.js and return the items list."""
    script = (
        "let _c=null;"
        "global.__NUXT_JSONP__=function(p,d){_c=d;};\n"
        + payload_js
        + "\n;function _findItems(o,d){"
        "if(d>10||!o)return [];"
        "if(Array.isArray(o)){if(o.length>0&&o[0]&&typeof o[0]==='object'"
        "&&(o[0].contentType==='event'||o[0].contentType==='tour'||o[0].contentType==='exhibition'))"
        "{return o;}"
        "let r=[];for(let i of o){r=r.concat(_findItems(i,d+1));if(r.length>0)break;}"
        "return r;}"
        "if(typeof o==='object'){let r=[];"
        "for(let v of Object.values(o)){r=r.concat(_findItems(v,d+1));if(r.length>0)break;}"
        "return r;}"
        "return [];}"
        "const items=_findItems(_c&&_c.data||[],0);"
        "process.stdout.write(JSON.stringify(items));"
    )

    with tempfile.NamedTemporaryFile(
        suffix=".js", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(
            ["node", tmp],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"node exited {result.returncode}: {result.stderr[:300]}")
        return json.loads(result.stdout) or []
    finally:
        os.unlink(tmp)


class Scraper(BaseScraper):
    venue_id = "getty_center"   # primary; villa events get venue_id overridden below
    events_url = "https://www.getty.edu/calendar/"
    source_label = "getty.edu"

    # Disable base strategies
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        # 1. Find build hash
        m = re.search(r"/_nuxt/static/(\d+)/", html)
        if not m:
            print(f"  [{self.venue_id}] could not find Nuxt build hash in HTML")
            return
        build_hash = m.group(1)

        # 2. Fetch payload
        payload_url = f"https://www.getty.edu/_nuxt/static/{build_hash}/calendar/payload.js"
        resp = get(payload_url)
        if not resp or not resp.ok:
            print(f"  [{self.venue_id}] payload.js fetch failed: {payload_url}")
            return

        # 3. Execute with Node.js
        try:
            items = _extract_events_node(resp.text)
        except Exception as e:
            print(f"  [{self.venue_id}] Node.js extraction failed: {e}")
            return

        print(f"  [{self.venue_id}] payload items: {len(items)}")

        # 4. Yield events
        seen: set[str] = set()
        for item in items:
            for ev in self._item_to_events(item):
                if ev.id not in seen:
                    seen.add(ev.id)
                    yield ev

    def _item_to_events(self, item: dict) -> list[Event]:
        content_type = item.get("contentType", "event")
        title = (item.get("title") or "").strip()
        if not title:
            return []

        href = item.get("href") or ""
        url = ("https://www.getty.edu" + href) if href.startswith("/") else href or None
        image_obj = item.get("image") or {}
        image = image_obj.get("url") or image_obj.get("src") if isinstance(image_obj, dict) else None
        location_list = item.get("location") or []
        venue_id = _infer_venue(location_list)
        location_label = _location_label(location_list)
        categories = item.get("category") or []
        event_type = _category_to_type(categories, title)
        subtitle = (item.get("subtitle") or "").strip()
        desc = (item.get("excerpt") or subtitle or "").strip()

        if content_type == "exhibition":
            date_obj = item.get("date") or {}
            if isinstance(date_obj, dict):
                start = to_la_iso(date_obj.get("startDate"))
                end = to_la_iso(date_obj.get("endDate"))
            else:
                start = end = None
            return [Event(
                id=event_id(venue_id, start, title + "::exh"),
                venue_id=venue_id,
                title=title,
                description=desc[:800],
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=image,
                location_override=location_label,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )]

        # Event or tour: date is a list of ISO strings (multiple occurrences)
        dates = item.get("date") or []
        if isinstance(dates, str):
            dates = [dates]
        if not dates:
            return []

        out = []
        for date_str in dates:
            start = to_la_iso(date_str)
            ev = Event(
                id=event_id(venue_id, start, title),
                venue_id=venue_id,
                title=title,
                description=desc[:800],
                event_type="tour" if content_type == "tour" else event_type,
                start=start,
                end=None,
                all_day=False,
                url=url,
                image=image,
                location_override=location_label,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
            out.append(ev)
        return out
