import { EVENT_TYPE_FILTERS, EVENTFUL_TYPES } from "./constants.js";

// Pure helpers for filtering + enriching venue/event data.

export function indexVenues(venues) {
  return Object.fromEntries(venues.map((v) => [v.id, v]));
}

// An event may carry several types (e.g. a performance that is also a
// screening). New records store them in `event_types`; older/archive records
// only have the single `event_type`. Always read through this helper.
export function eventTypesOf(ev) {
  if (ev.event_types && ev.event_types.length) return ev.event_types;
  return ev.event_type ? [ev.event_type] : [];
}
export function isExhibition(ev) {
  return eventTypesOf(ev).includes("exhibition");
}

// Scraped datetimes are stored as LA wall-clock (with an LA UTC offset), and
// the whole site speaks LA time. Parse the wall-clock fields verbatim instead
// of letting Date apply the viewer's timezone — otherwise a 6 PM event renders
// as "1 AM" for a UTC visitor, and a bare "2026-06-13" all-day date (UTC
// midnight per the ISO spec) renders as June 12 even in LA.
const ISO_WALL_RE = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/;

export function parseDate(s) {
  if (!s) return null;
  if (typeof s === "string") {
    const m = ISO_WALL_RE.exec(s);
    if (m) {
      return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0));
    }
  }
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
    if (!eventTypesOf(ev).some((t) => EVENTFUL_TYPES.has(t))) continue;
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

  if (preset === "today") {
    // Everything happening today: start of today through 23:59 tonight.
    const end = new Date(today0);
    end.setHours(23, 59, 59, 999);
    return { start: today0, end };
  }

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
    if (rawEventTypes && !eventTypesOf(ev).some((t) => rawEventTypes.has(t))) return false;
    if (regions && regions.size > 0 && !regions.has(venue.region)) return false;
    const evStart = parseDate(ev.start);
    const evEnd = eventEnd(ev) || evStart;
    // When a date window is active (e.g. "Today"), an event with no date can't
    // be placed inside it — exclude it rather than letting it pass every window.
    if ((start || end) && !evStart) return false;
    if (start && evEnd && evEnd < start) return false;
    if (end && evStart && evStart > end) return false;
    return true;
  });
}

/** Case-insensitive text search across an event's own fields + its venue. */
export function searchEvents(events, venuesById, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return events;
  return events.filter((ev) => {
    const venue = venuesById[ev.venue_id];
    return [
      ev.title, ev.description, ev.location_override,
      venue?.name, venue?.neighborhood,
      ...(ev.artists || []),
    ].some((s) => s && s.toLowerCase().includes(q));
  });
}

/** Case-insensitive text search across venue fields. */
export function searchVenues(venues, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return venues;
  return venues.filter((v) =>
    [v.name, v.description, v.neighborhood, v.address]
      .some((s) => s && s.toLowerCase().includes(q))
  );
}

/** Split a flat events array into one-off events vs. exhibitions. */
export function partitionByMode(events) {
  const oneoff = [];
  const exhibitions = [];
  for (const ev of events) {
    if (isExhibition(ev)) exhibitions.push(ev);
    else oneoff.push(ev);
  }
  return { oneoff, exhibitions };
}

/**
 * The Exhibitions tab shows ONLY real, temporary exhibitions that are on view
 * today. Everything else is excluded:
 *   - not typed `exhibition` (events, tours, workshops…)
 *   - tour / program records that slipped in as exhibitions (title heuristic)
 *   - missing a real open AND close date (can't place or sort it)
 *   - not currently open (opens in the future, or already closed)
 *   - permanent / long-term installations (runs longer than ~18 months)
 */
const EXHIBITION_MAX_DAYS = 550; // ~18 months; longer ⇒ treat as permanent
const NON_EXHIBITION_TITLE = new RegExp(
  "\\b(permanent|tour|tours|supper|suppers|sips|party|happy hour|story hour|" +
  "drop[- ]?in|skate|tasting|brunch|meet[- ]?up|class|workshop)\\b",
  "i"
);

export function isLiveTemporaryExhibition(ev, now = new Date()) {
  if (!ev || !isExhibition(ev)) return false;
  if (NON_EXHIBITION_TITLE.test(ev.title || "")) return false;
  const s = parseDate(ev.start);
  const e = parseDate(ev.end);
  if (!s || !e) return false;                       // need both bounds
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (s > today0) return false;                     // not yet opened
  if (e < today0) return false;                     // already closed
  if ((e - s) / 864e5 > EXHIBITION_MAX_DAYS) return false; // permanent
  return true;
}

export function liveExhibitionsOnView(exhibitions, now = new Date()) {
  return exhibitions.filter((ev) => isLiveTemporaryExhibition(ev, now));
}

/** Sort by closing date ascending — exhibitions ending soonest come first. */
export function sortByEndingSoonest(events) {
  const far = new Date("9999-01-01");
  return [...events].sort((a, b) => {
    const ae = parseDate(a.end) || parseDate(a.start) || far;
    const be = parseDate(b.end) || parseDate(b.start) || far;
    return ae - be;
  });
}

export function sortEvents(events) {
  return [...events].sort((a, b) => {
    const aS = parseDate(a.start) || new Date("9999-01-01");
    const bS = parseDate(b.start) || new Date("9999-01-01");
    return aS - bS;
  });
}

/**
 * Returns a proximity label for an event card:
 *   "Now"          — event is currently in progress
 *   "Today"        — starts today
 *   "Tomorrow"     — starts tomorrow
 *   "This weekend" — starts Fri/Sat/Sun within 7 days
 *   "This week"    — starts within 7 days
 *   null           — further away, no label needed
 */
export function getRelativeLabel(ev, now = new Date()) {
  const start = parseDate(ev.start);
  if (!start) return null;
  const end = eventEnd(ev);

  // Currently in progress (but not a long-running exhibition)
  if (!isExhibition(ev) && end && start <= now && end >= now) {
    return "Now";
  }

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const eventDay = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const diffDays = Math.round((eventDay - today) / 864e5);

  if (diffDays < 0) return null;
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  const dow = start.getDay(); // 0=Sun, 5=Fri, 6=Sat
  if (diffDays <= 7 && (dow === 5 || dow === 6 || dow === 0)) return "This weekend";
  if (diffDays <= 7) return "This week";
  return null;
}
