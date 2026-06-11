"""Headless-browser renderer (subprocess entry point).

A handful of venue sites (Norton Simon behind Cloudflare, Huntington behind
Vercel's "Security Checkpoint") serve an event-less shell — or a hard 429 — to
plain HTTP clients, but hand a real browser the full calendar once its
anti-bot JavaScript has run. This script drives headless Chromium via
Playwright to fetch the fully-rendered HTML for one or more URLs.

It runs as its own process (invoked by `render.py`) for two reasons:
  1. Playwright's sync API must own its thread; run_all scrapes venues in a
     thread pool, so doing the render in a subprocess sidesteps that entirely
     (the same trick the Getty scraper uses to run Node).
  2. If Playwright/Chromium isn't installed (e.g. a quick local `run_all`),
     this exits cleanly with null results instead of breaking the import graph.

Usage:
    python -m scrapers.utils.render_cli URL [URL ...]
Output (stdout): JSON object mapping each URL to its rendered HTML (or null).
"""
from __future__ import annotations

import json
import re
import sys

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Titles served by bot-protection interstitials. While the page title still
# matches one of these, the real content hasn't loaded yet.
_CHALLENGE_RE = re.compile(
    r"just a moment|security checkpoint|attention required|"
    r"verify you are human|checking your browser|please wait",
    re.IGNORECASE,
)

# Hide the two headless tells Vercel's checkpoint keys on so it runs its
# proof-of-work and self-clears instead of holding us at 429. Kept deliberately
# minimal: piling on more navigator overrides (plugins/languages) actually made
# the checkpoint stick, so we set only `navigator.webdriver` and `window.chrome`.
_STEALTH = (
    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    "window.chrome={runtime:{}};"
)

CHALLENGE_WAIT_MS = 30000   # max time to let an anti-bot interstitial self-clear
SETTLE_MS = 2500            # extra time for client-side rendering after clearance


def _render(context, url: str) -> str | None:
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Let any anti-bot interstitial run its own JS and auto-advance. The key
        # is to WAIT in-page rather than re-navigate (re-navigating restarts the
        # challenge), which is what lets Vercel's checkpoint clear itself.
        # Let any anti-bot interstitial run its own JS and auto-advance — wait
        # in-page (do NOT re-navigate, which restarts the challenge).
        waited = 0
        while waited < CHALLENGE_WAIT_MS:
            page.wait_for_timeout(2000)
            waited += 2000
            if not _CHALLENGE_RE.search(page.title() or ""):
                break
        if _CHALLENGE_RE.search(page.title() or ""):
            sys.stderr.write(
                f"[render] {url}: still challenged after {waited}ms "
                f"(last title: {page.title()!r})\n"
            )
            return None
        # Best-effort wait for the SPA to finish populating, then settle.
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(SETTLE_MS)
        return page.content()
    except Exception as e:
        sys.stderr.write(f"[render] {url}: {type(e).__name__}: {e}\n")
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


def main(argv=None) -> int:
    urls = list(argv if argv is not None else sys.argv[1:])
    if not urls:
        print("{}")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sys.stderr.write("[render] playwright not installed; returning nulls\n")
        print(json.dumps({u: None for u in urls}))
        return 0

    out: dict[str, str | None] = {u: None for u in urls}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--ignore-certificate-errors",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent=_UA,
                locale="en-US",
                viewport={"width": 1366, "height": 900},
            )
            context.add_init_script(_STEALTH)
            for u in urls:
                out[u] = _render(context, u)
            browser.close()
    except Exception as e:
        sys.stderr.write(f"[render] browser launch failed: {e}\n")

    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
