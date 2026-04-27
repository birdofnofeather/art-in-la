"""Diagnostic crawler. Runs once via the `explore` workflow.

For every venue with an `events_url` set, fetch that page (and a few common
auxiliary URLs that often expose machine-readable data) and write a structural
summary to scrapers/_findings.md. The summary is what a human (or model) can
use to decide which extraction strategy will work without having to inspect
each site by hand.

The output is intentionally Markdown so it diffs cleanly in the repo.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 ArtInLA/explore"
)
TIMEOUT = 20


def fetch(url: str) -> tuple[int | None, str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
        return r.status_code, r.text, r.url
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", url


def origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def jsonld_types(body: str) -> list[str]:
    """Extract @type strings from every JSON-LD block on the page."""
    types: set[str] = set()
    blocks = re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
        body, re.S | re.I,
    )
    for blob in blocks:
        try:
            data = json.loads(blob.strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                t = node.get("@type")
                if t:
                    if isinstance(t, list):
                        types.update(str(x) for x in t)
                    else:
                        types.add(str(t))
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return sorted(types)


def first_jsonld_event_sample(body: str) -> str | None:
    """Pull the first JSON-LD object whose type contains 'event'."""
    blocks = re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
        body, re.S | re.I,
    )
    for blob in blocks:
        try:
            data = json.loads(blob.strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                t = node.get("@type")
                ts = []
                if isinstance(t, list):
                    ts = [str(x).lower() for x in t]
                elif t:
                    ts = [str(t).lower()]
                if any("event" in x for x in ts):
                    keep = {k: v for k, v in node.items() if k in {
                        "@type", "name", "startDate", "endDate", "url",
                        "location", "description", "image", "performer",
                    }}
                    out = json.dumps(keep, indent=2, default=str)
                    return out[:1500]
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return None


def probe(venue_id: str, events_url: str) -> str:
    out = [f"## {venue_id}", f"- events_url: `{events_url}`"]

    st, body, final = fetch(events_url)
    out.append(f"- main fetch: status={st}, bytes={len(body) if isinstance(body, str) else 0}, final={final}")

    if st != 200 or not isinstance(body, str):
        out.append(f"- ERROR body: `{body[:200]}`")
        # Even on error, try the probes below; the final URL may still be useful.

    if st == 200 and isinstance(body, str):
        types = jsonld_types(body)
        out.append(f"- jsonld @types: {types if types else '(none)'}")
        sample = first_jsonld_event_sample(body)
        if sample:
            out.append("- first event-like JSON-LD object:")
            out.append("```json")
            out.append(sample)
            out.append("```")

        signals = []
        if "/wp-content/" in body or "/wp-json/" in body:
            signals.append("wordpress")
        if "tribe-events" in body or "tribe_events" in body:
            signals.append("tribe-events")
        if "drupal" in body.lower() or 'data-drupal' in body:
            signals.append("drupal")
        if "BEGIN:VCALENDAR" in body[:500]:
            signals.append("ical-direct")
        if "?ical=1" in body:
            signals.append("ical-link")
        if "fullcalendar" in body.lower():
            signals.append("fullcalendar")
        if re.search(r'<link[^>]+rss', body, re.I) or re.search(r'<link[^>]+feed', body, re.I):
            signals.append("rss-link")
        if "next/data" in body or '__NEXT_DATA__' in body:
            signals.append("nextjs")
        out.append(f"- platform signals: {signals or '(none)'}")

    # Probe common auxiliary URLs.
    base = origin(events_url)
    probes = [
        ("/wp-json/tribe/events/v1/events?per_page=5", "tribe-rest"),
        ("/events/?ical=1", "tribe-ical"),
        ("/event/?ical=1", "tribe-ical-singular"),
        ("/sitemap.xml", "sitemap-root"),
        ("/event-sitemap.xml", "sitemap-events"),
        ("/feed/", "wp-rss"),
        ("/events/feed/", "wp-rss-events"),
        ("/api/events", "rest-api-events"),
    ]
    for path, label in probes:
        url = urljoin(base + "/", path.lstrip("/"))
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
            ct = r.headers.get("Content-Type", "")[:40]
            preview = r.text[:120].replace("\n", " ")
            out.append(f"- probe `{label}` {url} -> {r.status_code} ({ct}); `{preview}…`")
        except Exception as e:
            out.append(f"- probe `{label}` {url} -> ERR {type(e).__name__}")

    out.append("")
    return "\n".join(out)


def load_venues(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    venues = load_venues(repo_root / "public" / "data" / "venues.json")
    venues_to_probe = [v for v in venues if v.get("events_url")]

    # Optional filter via comma-separated venue ids.
    only = os.environ.get("ART_IN_LA_EXPLORE_VENUES", "").strip()
    if only:
        wanted = {x.strip() for x in only.split(",")}
        venues_to_probe = [v for v in venues_to_probe if v["id"] in wanted]

    print(f"Probing {len(venues_to_probe)} venues…", file=sys.stderr)
    sections = []
    for v in venues_to_probe:
        print(f"  - {v['id']}", file=sys.stderr)
        sections.append(probe(v["id"], v["events_url"]))

    findings = (
        "# Venue site findings\n\n"
        "Auto-generated by `scrapers/explore.py` via the `explore` workflow.\n"
        "Each entry shows what's actually on each venue's events page so the\n"
        "right scraping strategy can be chosen.\n\n"
        + "\n".join(sections)
    )
    out_path = repo_root / 