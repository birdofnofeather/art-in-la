"""Ruth Chandler Williamson Gallery, Scripps College.

The college publishes a WordPress "The Events Calendar" feed covering the whole
campus, so the base scraper's wp_tribe strategy reads it directly. Non-gallery
campus events are filtered out below — without that this venue would flood the
listing with lectures and athletics.
"""
from ..base import BaseScraper

# Only keep events that actually concern the gallery or its exhibitions.
_GALLERY_WORDS = (
    "williamson", "gallery", "exhibition", "art", "artist", "museum",
    "ceramic", "print", "curator", "collection",
)


class Scraper(BaseScraper):
    venue_id = "williamson_scripps"
    events_url = "https://www.scrippscollege.edu/events"
    source_label = "scrippscollege.edu"

    def run(self):
        events = super().run()
        kept = []
        for ev in events:
            text = f"{ev.get('title','')} {ev.get('description','')}".lower()
            if any(word in text for word in _GALLERY_WORDS):
                kept.append(ev)
        if len(kept) != len(events):
            print(f"  [{self.venue_id}] kept {len(kept)}/{len(events)} "
                  f"campus events that concern the gallery")
        return kept
