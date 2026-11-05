"""Shared base for venues whose calendar only exists after JavaScript runs.

Their plain HTML is an empty shell, so the page is rendered in headless
Chromium (utils/render.py — available in CI; a plain local run simply gets
nothing). Parsers here were written against snapshots of each site taken from
GitHub's runners (.github/workflows/snapshot.yml → debug-snapshots branch).
If rendering is unavailable or the markup changes, the base chain falls
through to the LLM reader, then the monitor/repair tiers.
"""
from __future__ import annotations

from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.render import render_page


class RenderedScraper(BaseScraper):
    squarespace = False

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    def _strategy_squarespace(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        html = render_page(self.events_url)
        if not html:
            return
        yield from self.custom_parse(html, self.events_url)
