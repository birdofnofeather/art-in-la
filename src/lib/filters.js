import { EVENT_TYPE_FILTERS, EVENTFUL_TYPES } from "./constants.js";

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

/** Apply org-level filters (type, region, eventful). */
export function filterVenues(venues, { types, regions, eventful, eventfulIds }) {
  return venues.filter((v) => {
    if (types && types.size > 0 && !types.has(v.type)) return false;
    if (regions && regions.size > 0 && !regions.has(v.region)) return false;
    if (eventful && !eventfulIds.has(v.id)) return false;
    return true;
  });
}

// Translate a Set of EVENT_TYPE_FILTERS keys (e.g. "openingclosing") into
// the raw event_type strings stored on event records.
function expandEventTypes(eventTypeKeys) {
  if (!eventTypeKeys || eventTypeKeys.size === 0) return null;
  const raw = new Set();
  for (const f of EVENT_TYPE_FILTERS) {
    if (eventTypeKeys.has(f.key)) {
      for (const m of f.matches) raw.add(m);
    }
  }
  return raw;
}

/**
 * Resolve a date-preset key into an inclusive [start, end] window.
 * Returns { start: null, end: null } for "all" / unrecognized.
 */
export function resolveDatePreset(preset, now = new Date()) {
  if (!preset || preset === "all") return { start: null, end: null };
  const today0 = new Date(now); today0.setHours(0, 0, 0, 0);
  const day = today0.getDay(); // 0 = Sun, 6 = Sat

  if (preset === "weekend") {
    // Window: from upcoming (or today's) Friday morning through Sunday 23:59.
    let start;
    if (day === 5 || day === 6 || day === 0) {
      // Already in the weekend window — use now so we don't include past hours.
      start = new Date(now);
    } else {
      const daysToFri = 5 - day;
      start = new Date(today0);
      start.setDate(today0.getDate() + daysToFri);
    }
    const daysToSun = day === 0 ? 0 : 7 - day;
    const end = new Date(today0);
    end.setDate(today0.getDate() + daysToSun);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  }

  if (preset === "nextweek") {
    // Mon of next week through Sun of next week (i.e. includes the upcoming weekend).
    const offset = day === 0 ? 1 : 8 - day; // Sun→+1, Mon→+7, … Sat→+2
    const start = new Date(today0);
    start.setDate(today0.getDate() + offset);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  }

  if (preset === "month") {
    // From now through the last day of the current calendar month.
    const start = new Date(now);
    const end = new Date(today0.getFullYear(), today0.getMonth() + 1, 0);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  }

  return { start: null, end: null };
}

/** Apply event-level filters (venue type, event type, date range / preset). */
export function filterEvents(events, venuesById, {
  venueTypes, eventTypes, regions, datePreset, startDate, endDate,
}) {
  const rawEventTypes = expandEventTypes(eventTypes);
  let start = null, end = null;
  if (datePreset && datePreset !== "all") {
    ({ start, end } = resolveDatePreset(datePreset));
  } else {
    if (startDate) start = new Date(startDate);
    if (endDate) end = new Date(endDate + "T23:59:59");
  }
  return events.filter((ev) => {
    const venue = venuesById[ev.venue_id];
    if (!venue) return false;
    if (venueTypes && venueTypes.size > 0 && !venueTypes.has(venue.type)) return false;
    if (rawEventTypes && !rawEventTypes.has(ev.event_type)) return false;
    if (regions && regions.size > 0 && !regions.has(venue.region)) return false;
    const evStart = parseDate(ev.start);
    const evEnd = eventEnd(ev) || evStart;
    if (start && evEnd && evEnd < start) return false;
    if (end && evStart && evStart > end) return false;
    return true;
  });
}

/** Split a flat events array into one-off events vs. exhibitions. */
export function partitionByMode(events) {
  const oneoff = [];
  const exhibitions = [];
  for (const ev of events) {
    if (ev.event_type === "exhibition") exhibitions.push(ev);
    else oneoff.push(ev);
  }
  return { oneoff, exhibitions };
}

/**
 * Filter exhibitions by status.
 *   current: start <= now <= end (or no end yet)
 *   upcoming: start > now
 *   all: everything that hasn't ended yet
 */
export function filterExhibitions(exhibitions, status, now = new Date()) {
  return exhibitions.filter((ev) => {
    const s = parseDate(ev.start);
    const e = parseDate(ev.end);
    // Skip exhibitions whose end has already passed.
    if (e && e < now) return false;
    if (status === "current") {
      if (!s) return false;
      if (s > now) return false;          // hasn't opened
      return !e || e >= now;              // still on view
    }
    if (status === "upcoming") {
      if (!s) return false;
      return s > now;                     // opens in the future
    }
    // "all" (or unrecognized) — return everything not-yet-closed.
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
