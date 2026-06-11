"""Fetch fully-rendered HTML for bot-gated venues via a headless browser.

Thin wrapper around `render_cli.py`, which it runs as a subprocess so the
heavyweight, thread-unfriendly Playwright work stays isolated from the scraper
thread pool. Degrades gracefully: if Playwright/Chromium isn't installed or the
render fails, every URL comes back as None and the calling scraper simply
produces no events (its previously-scraped events carry over).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from typing import Iterable, Optional


def _playwright_available() -> bool:
    try:
        return importlib.util.find_spec("playwright") is not None
    except Exception:
        return False


def render_pages(urls: Iterable[str], *, timeout: int = 240) -> dict[str, Optional[str]]:
    """Return {url: rendered_html_or_None}. Never raises."""
    urls = list(urls)
    if not urls:
        return {}
    if not _playwright_available():
        print("  [render] playwright not installed — skipping rendered venue")
        return {u: None for u in urls}

    cmd = [sys.executable, "-m", "scrapers.utils.render_cli", *urls]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"  [render] timed out after {timeout}s")
        return {u: None for u in urls}
    except Exception as e:
        print(f"  [render] subprocess error: {e}")
        return {u: None for u in urls}

    if res.returncode != 0:
        print(f"  [render] exited {res.returncode}: {res.stderr[:300]}")
        return {u: None for u in urls}
    try:
        data = json.loads(res.stdout)
    except Exception:
        print(f"  [render] unparseable output: {res.stdout[:200]}")
        return {u: None for u in urls}
    # Surface the renderer's own diagnostics without failing the run.
    if res.stderr.strip():
        for line in res.stderr.strip().splitlines()[:6]:
            print(f"  {line}")
    return data


def render_page(url: str, *, timeout: int = 120) -> Optional[str]:
    return render_pages([url], timeout=timeout).get(url)
