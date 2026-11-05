"""18th Street Arts Center — WordPress + The Events Calendar (Tribe) REST API."""
from dataclasses import replace

from ..base import BaseScraper, _exhibition_threshold
from ..utils.event_id import event_id


class Scraper(BaseScraper):
    venue_id = "18th_street"
    events_url = "https://www.18thstreet.org/events/"
    source_label = "18thstreet.org"
    # Post-process ON: Tribe lists exhibitions as multi-week "events"; they must
    # be re-typed as exhibitions or the hygiene gate drops them as one-offs
    # spanning weeks (RED ALL NIGHTmare, Ghost Agency, The Final Rally).
    drop_exhibitions: bool = True

    def _reshape(self, ev):
        # 18th Street files its exhibitions under Tribe categories such as
        # "Screening" or "Opening", which the base class never promotes. Any
        # record here spanning weeks is an exhibition, whatever its category.
        dur = self._duration(ev)
        if ev.event_type != "exhibition" and dur is not None and dur > _exhibition_threshold():
            if self._is_permanent(ev):
                return None
            return replace(ev, id=event_id(self.venue_id, ev.start, ev.title + "::exh"),
                           event_type="exhibition")
        return super()._reshape(ev)

