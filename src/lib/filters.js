import { EVENTFUL_TYPES } from "./constants.js";

// Pure helpers for filtering + enriching venue/event data.

export function indexVenues(venues) {
  return Object.fromEntries(venues.map((v) => [v.id, v]));
}

export function parseDate(s) {
  if (!s) return null;
  const d = new Date(s);
  return Number.isNaN(+d) ? null : d;
}

export function eventEnd(ev) {
  return parseDate(ev.end) || parseDate(ev.start);
}

export function isUpcoming(ev, now = new Date()) {
  const end = eventEnd(ev);
  if (!end) return true;
  return end >= now;
}

/** Returns a Set of venue_ids that have any "eventful" upcoming event. */
export function eventfulVenueIds(events) {
  const now = new Date();
  const ids = new Set();
  for (const ev of events) {
    if (!isUpcoming(ev, now)) continue;
    if (!EVENTFUL_TYPES.has(ev.event_type)) continue;
    ids.add(ev.venue_id);
  }
  return ids;
}

/** Apply org-level filters (type, region). */
export function filterVenues(venues, { types, regions, eventful, eventfulIds }) {
  return venues.filter((v) => {
    if (types && types.size > 0 && !types.has(v.type)) return false;
    if (regions && regions.size > 0 && !regions.has(v.region)) return false;
    if (eventful && !eventfulIds.has(v.id)) return false;
    return true;
  });
}

/** Apply event-level filters (venue type, event type, date range). */
export function filterEvents(events, venuesById, {
  venueTypes, eventTypes, regions, startDate, endDate,
}) {
  const start = startDate ? new Date(startDate) : null;
  const end = endDate ? new Date(endDate + "T23:59:59") : null;
  return events.filter((ev) => {
    const venue = venuesById[ev.venue_id];
    if (!venue) return false;
    if (venueTypes && venueTypes.size > 0 && !venueTypes.has(venue.type)) return false;
    if (eventTypes && eventTypes.size > 0 && !eventTypes.has(ev.event_type)) return false;
    if (regions && regions.size > 0 && !regions.has(venue.region)) return false;
    const evStart = parseDate(ev.start);
    const evEnd = eventEnd(ev) || evStart;
    if (start && evEnd && evEnd < start) return false;
    if (end && evStart && evStart > end) return false;
    return true;
  });
}

export function sortEvents(events) {
  return [...events].sort((a, b) => {
    const aS = parseDate(a.start) || new Date("9999-01-01");
    const bS = parseDate(b.start) || new Date("9999-01-01");
    return aS - bS;
  });
}
