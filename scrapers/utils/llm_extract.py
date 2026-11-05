"""The LLM reading tier — Claude Haiku reads a venue page the parsers can't.

Two jobs, both gated on the ANTHROPIC_API_KEY environment variable (a GitHub
Actions secret in CI). Without the key every function here is a silent no-op,
so the pipeline behaves exactly as it did before this tier existed.

1. `extract_listing()` — read an events or exhibitions page and return the
   listings on it. Used (a) for venues with no feed and no reliable HTML
   pattern, and (b) automatically, as SELF-HEALING, when a venue's normal
   scraper returns nothing or collapses far below its recent output (its site
   was redesigned). Fixes the DATA, not the code — code repair is the separate,
   rarer tier in .github/workflows/repair-scraper.yml.

2. `recover()` — for single events dropped for a missing date, read the event's
   own page and recover the date.

Cost control (the owner's requirement: a few dollars a month, never more):

* Cache by page content. A page is sent to the model only when its visible
  text has changed since the last read; otherwise the stored answer is reused.
  Most venue pages change a few times a month, so most days cost nothing.
* A hard monthly budget (LLM_MONTHLY_BUDGET_USD, default $3). Spend is metered
  from the API's own token counts into scrapers/state/llm_ledger.json, which
  CI commits. Once the month's budget is used up, calls stop until the 1st.
* A per-run cap on calls (LLM_MAX_CALLS_PER_RUN, default 40).

Hallucination control — nothing the model says is trusted on its own:

* Output is constrained to a JSON schema (structured outputs).
* Every title must actually appear in the page text (normalised match), and
  the item's day-of-month must appear near it. Anything else is discarded.
* Dates must parse and fall inside a sane window.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from .http import get
from .dateparse import to_la_iso

MODEL = "claude-haiku-5-5"
# Published per-million-token prices for MODEL (prompts under 100K tokens).
PRICE_IN_PER_M = 0.10
PRICE_OUT_PER_M = 0.50

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
CACHE_PATH = STATE_DIR / "llm_cache.json"
LEDGER_PATH = STATE_DIR / "llm_ledger.json"

MAX_PAGE_CHARS = 60_000          # ~15K tokens; long pages are cut at item boundaries
CACHE_TTL_DAYS = 21              # re-read an unchanged page at least this often
_LOCK = threading.Lock()
_calls_this_run = 0


def enabled() -> bool:
    # Dry runs (local checks, the repair agent's verification) never call the
    # model: they must test the real parser, and must not spend unmetered.
    if os.environ.get("ART_IN_LA_DRY_RUN"):
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _budget() -> float:
    try:
        return float(os.environ.get("LLM_MONTHLY_BUDGET_USD", "3"))
    except ValueError:
        return 3.0


def _max_calls() -> int:
    try:
        return int(os.environ.get("LLM_MAX_CALLS_PER_RUN", "150"))
    except ValueError:
        return 150


# ── persistent state (cache + ledger) ─────────────────────────────────────
def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: dict) -> None:
    if os.environ.get("ART_IN_LA_DRY_RUN"):
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def spent_this_month() -> float:
    return float(_load(LEDGER_PATH).get(_month(), {}).get("usd", 0.0))


def _record_spend(in_tok: int, out_tok: int, purpose: str) -> None:
    usd = in_tok / 1e6 * PRICE_IN_PER_M + out_tok / 1e6 * PRICE_OUT_PER_M
    with _LOCK:
        led = _load(LEDGER_PATH)
        m = led.setdefault(_month(), {"usd": 0.0, "calls": 0, "input_tokens": 0,
                                      "output_tokens": 0, "by_purpose": {}})
        m["usd"] = round(m["usd"] + usd, 5)
        m["calls"] += 1
        m["input_tokens"] += in_tok
        m["output_tokens"] += out_tok
        m["by_purpose"][purpose] = m["by_purpose"].get(purpose, 0) + 1
        _save(LEDGER_PATH, led)


def _may_call() -> bool:
    global _calls_this_run
    if not enabled():
        return False
    with _LOCK:
        if _calls_this_run >= _max_calls():
            return False
        if spent_this_month() >= _budget():
            print(f"  [llm] monthly budget ${_budget():.2f} reached — skipping")
            return False
        _calls_this_run += 1
        return True


# ── page → text the model (and the validator) can read ───────────────────
def page_text(html: str, base_url: str = "") -> str:
    """Visible text with link targets kept inline as <url>, nav/footer removed."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(["script", "style", "noscript", "svg", "iframe", "form",
                            "nav", "footer", "header"]):
        t.decompose()
    root = soup.find("main") or soup.body or soup
    for a in root.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("http", "/")) and a.get_text(strip=True):
            if href.startswith("/") and base_url:
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            a.append(f" <{href}>")
    for br in root.find_all(["br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr", "article", "section"]):
        br.insert_before("\n")
    text = root.get_text(" ")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    if len(text) > MAX_PAGE_CHARS:
        cut = text.rfind("\n", 0, MAX_PAGE_CHARS)
        text = text[: cut if cut > 0 else MAX_PAGE_CHARS]
    return text


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[‘’“”'\"“”‘’]", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ── the model call ─────────────────────────────────────────────────────────
_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "kind": {"type": "string", "enum": ["event", "exhibition"]},
                    "start_date": {"type": "string"},
                    "end_date": {"type": ["string", "null"]},
                    "start_time": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "price_text": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                },
                "required": ["title", "kind", "start_date", "end_date", "start_time",
                             "url", "price_text", "description"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

_LISTING_PROMPT = """You are reading the {mode} page of {venue}, an arts venue in Los Angeles{where}.
Today is {today}. Extract every individual {mode_noun} listed on the page below.

Rules:
- If the page lists several sites of the same organization, include only items at this venue's
  site{where_rule}.
- Skip closures, holiday hours, and "museum closed" notices — they are not events.
- Copy each title EXACTLY as written on the page (no rewording, no added words).
- Only include items that show a specific date on this page. Skip items with no date.
- Skip navigation, newsletters, membership, donation, venue-rental, and shop items.
- Skip anything that has already ended before today.
- Dates as YYYY-MM-DD. If the page omits the year, use the next occurrence on or after today
  (for an exhibition already open, the year that makes the range include today).
- start_time as 24-hour HH:MM only if a time is printed for that item, else null. Never invent a time.
- For an exhibition or a multi-day run, give end_date; otherwise null.
- kind = "exhibition" for an art exhibition/installation on view over a date range; otherwise "event".
- url = the item's own link if one appears next to it (shown in <angle brackets>), else null.
- price_text like "Free", "$15", "$10–$25" only if printed, else null.
- description: one short factual sentence from the page, or null.

PAGE TEXT:
{text}"""


def _ask(prompt: str, purpose: str, max_tokens: int = 8000) -> dict | None:
    if not _may_call():
        return None
    try:
        import anthropic
    except ImportError:
        print("  [llm] anthropic package not installed — skipping")
        return None
    try:
        client = anthropic.Anthropic(max_retries=2, timeout=120)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            output_config={"effort": "low",
                           "format": {"type": "json_schema", "schema": _ITEM_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        print(f"  [llm] API {e.status_code}: {str(e)[:160]}")
        return None
    except anthropic.APIConnectionError as e:
        print(f"  [llm] connection failed: {e}")
        return None
    except Exception as e:  # noqa: BLE001 — this optional tier must never crash a run
        print(f"  [llm] call failed: {type(e).__name__}: {e}")
        return None
    usage = getattr(resp, "usage", None)
    if usage is not None:
        _record_spend(usage.input_tokens or 0, usage.output_tokens or 0, purpose)
    if resp.stop_reason in ("refusal", "max_tokens"):
        print(f"  [llm] stop_reason={resp.stop_reason} — ignoring answer")
        return None
    text = next((getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text"), "")
    try:
        got = json.loads(text)
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


# ── validation: keep only what the page itself supports ──────────────────
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validate_items(items: list, text: str, today: date | None = None) -> list[dict]:
    today = today or date.today()
    page = _norm(text)
    out, seen = [], set()
    for it in items or []:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        nt = _norm(title)
        if len(nt) < 3 or len(title) > 200:
            continue
        pos = page.find(nt)
        if pos < 0:
            continue                                   # title not on the page → invented
        sd = it.get("start_date") or ""
        if not _ISO.match(sd):
            continue
        try:
            start = date.fromisoformat(sd)
        except ValueError:
            continue
        end = None
        if it.get("end_date") and _ISO.match(it["end_date"]):
            try:
                end = date.fromisoformat(it["end_date"])
            except ValueError:
                end = None
        if end and end < start:
            end = None
        if (end or start) < today - timedelta(days=1) or start > today + timedelta(days=550):
            continue
        # The day-of-month must be printed near the title (within the item's
        # neighbourhood of text) — catches dates the model made up.
        window = page[max(0, pos - 600): pos + len(nt) + 600]
        days = {str(start.day)}
        if end:
            days.add(str(end.day))
        if not any(re.search(rf"(?<!\d){d}(?!\d)", window) for d in days):
            continue
        # …and so must its month (by name, or numerically as in 11/12).
        mon = start.strftime("%b").lower()
        if not re.search(rf"\b{mon}", window) and not re.search(
                rf"(?<!\d)0?{start.month}[/.\-]0?{start.day}(?!\d)", window):
            continue
        key = (nt, start)
        if key in seen:
            continue
        seen.add(key)
        tm = it.get("start_time")
        tm = tm if isinstance(tm, str) and _HHMM.match(tm) and _time_on_page(tm, window) else None
        url = it.get("url") if isinstance(it.get("url"), str) and it["url"].startswith("http") else None
        out.append({
            "title": title,
            "kind": "exhibition" if it.get("kind") == "exhibition" else "event",
            "start": start, "end": end, "time": tm, "url": url,
            "price_text": (it.get("price_text") or None) and str(it["price_text"])[:24],
            "description": (it.get("description") or "")[:400],
        })
    return out


def _time_on_page(hhmm: str, window: str) -> bool:
    """Is this time actually printed near the item? An unsupported time is
    dropped — the item stays, date-only — because a fabricated time is worse
    than none. `window` is the normalised page text (punctuation → spaces,
    so "7:30 p.m." reads "7 30 p m" and "19:30" reads "19 30")."""
    h, m = int(hhmm[:2]), int(hhmm[3:])
    h12 = h % 12 or 12
    ap = "p" if h >= 12 else "a"
    mm = rf" {m:02d}" if m else r"(?: 00)?"
    pats = [
        # 7 pm · 7 30 pm · 7 30pm · 7 p m · 7 9 pm (range: start hour first)
        rf"(?<!\d){h12}{mm} ?(?:to )?(?:\d{{1,2}}(?: \d{{2}})? ?)?{ap} ?m\b",
        rf"(?<!\d){h12}{mm}{ap}m\b",
        rf"(?<!\d){h:02d} {m:02d}(?!\d)",
        rf"(?<!\d){h} {m:02d}(?!\d)" if h >= 13 else r"(?!x)x",
    ]
    if h == 12 and m == 0:
        pats.append(r"\bnoon\b")
    return any(re.search(p, window) for p in pats)


# ── public API ─────────────────────────────────────────────────────────────
# What the LLM reader saw this run, per venue: (items the model listed, items
# that passed validation). The monitor uses it as an independent second
# opinion — if the model read the page and found nothing upcoming, a raw date
# count on that page is past/undated listings, not a broken parser.
READS: dict[str, tuple[int, int]] = {}
MAX_RENDERS_PER_RUN = 25
_renders = 0


def _render(url: str) -> str | None:
    """Rendered HTML for JavaScript-built pages (headless Chromium, CI only)."""
    global _renders
    with _LOCK:
        if _renders >= MAX_RENDERS_PER_RUN:
            return None
        _renders += 1
    try:
        from .render import render_page
        return render_page(url)
    except Exception as e:  # noqa: BLE001
        print(f"  [llm] render failed for {url}: {e}")
        return None


def extract_listing(venue_id: str, venue_name: str, url: str, mode: str = "events",
                    html: str | None = None, force: bool = False, address: str = "") -> list[dict]:
    """Listings on `url` as validated dicts (see validate_items). [] when disabled.

    Reads the plain HTML first. If that has little text, or the model finds
    nothing on it, the page is probably built by JavaScript — so it is rendered
    in a headless browser (when available, i.e. in CI) and read again.
    """
    if not enabled():
        return []
    rendered = False
    if html is None:
        resp = get(url)
        if resp is not None and resp.ok:
            html, url = resp.text, resp.url
    text = page_text(html, url) if html else ""
    if len(text) < 1500:
        r = _render(url)
        if r:
            html, rendered = r, True
            text = page_text(html, url)
    if len(text) < 200:
        return []
    n_raw, kept = _read(venue_id, venue_name, url, mode, text, force, address, rendered)
    if n_raw == 0 and not rendered:
        r = _render(url)
        if r:
            text2 = page_text(r, url)
            if len(text2) >= 200 and text2 != text:
                n_raw, kept = _read(venue_id, venue_name, url, mode, text2, force, address, True)
    with _LOCK:
        prev = READS.get(venue_id, (0, 0))
        READS[venue_id] = (prev[0] + n_raw, prev[1] + len(kept))
    return kept


def _read(venue_id, venue_name, url, mode, text, force, address, rendered) -> tuple[int, list[dict]]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]
    key = f"{venue_id}|{mode}|{url}" + ("|rendered" if rendered else "")
    now = datetime.now(timezone.utc)
    with _LOCK:
        cached = _load(CACHE_PATH).get(key)
    if cached and not force and cached.get("hash") == digest:
        try:
            age = now - datetime.fromisoformat(cached["at"])
        except (KeyError, ValueError):
            age = timedelta(days=999)
        if age < timedelta(days=CACHE_TTL_DAYS):
            items = cached.get("items") or []
            print(f"  [{venue_id}] llm cache hit ({len(items)} items, page unchanged)")
            return len(items), validate_items(items, text)

    prompt = _LISTING_PROMPT.format(
        mode=mode, venue=venue_name, today=date.today().isoformat(),
        where=f" ({address})" if address else "",
        where_rule=f" ({address}); if an item's site is not stated, include it" if address else "",
        mode_noun="exhibition" if mode == "exhibitions" else "event or exhibition",
        text=text,
    )
    got = _ask(prompt, f"listing:{venue_id}")
    if got is None:
        # Budget exhausted / API down: fall back to the last good answer, if any.
        items = (cached or {}).get("items") or []
        return len(items), validate_items(items, text)
    raw_items = got.get("items") or []
    kept = validate_items(raw_items, text)
    print(f"  [{venue_id}] llm read {mode}{' (rendered)' if rendered else ''}: "
          f"{len(raw_items)} items, {len(kept)} passed validation")
    with _LOCK:
        cache = _load(CACHE_PATH)
        cache[key] = {"hash": digest, "at": now.isoformat(timespec="seconds"), "items": raw_items}
        _save(CACHE_PATH, cache)
    return len(raw_items), kept


_RECOVER_PROMPT = """From this event page, extract the event's date.
Event title: {title}
Today is {today}. Reply with an "items" list holding exactly one item for this event
(same rules: title copied exactly, dates YYYY-MM-DD, start_time HH:MM only if printed),
or an empty list if the page shows no date.

PAGE TEXT:
{text}"""


def recover(dropped: list[dict], max_items: int = 10) -> list[dict]:
    """Try to recover no-start-date drops by reading each event's own page."""
    if not enabled():
        return []
    out = []
    for ev in [e for e in dropped if not e.get("start") and e.get("url")][:max_items]:
        resp = get(ev["url"])
        if resp is None or not resp.ok:
            continue
        text = page_text(resp.text, resp.url)
        if len(text) < 80:
            continue
        got = _ask(_RECOVER_PROMPT.format(title=ev.get("title", ""), today=date.today().isoformat(),
                                          text=text[:12000]), "recover", max_tokens=1000)
        items = validate_items((got or {}).get("items") or [], text)
        if not items:
            continue
        it = items[0]
        fixed = dict(ev)
        fixed["start"] = to_la_iso(f"{it['start']}T{it['time']}" if it["time"] else it["start"].isoformat())
        fixed["end"] = to_la_iso(it["end"].isoformat()) if it["end"] else None
        fixed["all_day"] = it["time"] is None
        if it.get("price_text") and not fixed.get("price_text"):
            fixed["price_text"] = it["price_text"]
            if it["price_text"].lower() == "free" and fixed.get("is_free") is None:
                fixed["is_free"] = True
        fixed["source"] = (fixed.get("source") or "") + "+llm"
        out.append(fixed)
        print(f"  [llm] recovered: [{ev.get('venue_id')}] {ev.get('title','')[:50]} -> {fixed['start']}")
    return out
