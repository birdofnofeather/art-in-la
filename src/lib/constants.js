// Shared taxonomy and UI constants.

export const TYPE_LABEL = {
  museum: "Museum",
  gallery: "Gallery",
  community: "Community",
  alternative: "Alternative",
  academic: "Academic",
};

export const TYPE_COLOR = {
  museum: "#0f172a",
  gallery: "#b91c1c",
  community: "#15803d",
  alternative: "#7c3aed",
  academic: "#b45309",
};

export const TYPE_LETTER = {
  museum: "M",
  gallery: "G",
  community: "C",
  alternative: "X",
  academic: "A",
};

export const REGION_LABEL = {
  westside: "Westside",
  central: "Central",
  eastside: "Eastside / DTLA",
  northeast: "Northeast / Glendale",
  valley: "San Fernando Valley",
  south: "South LA",
  southbay: "South Bay",
  pasadena: "Pasadena / Foothills",
  longbeach: "Long Beach / Harbor",
  antelope: "Antelope Valley",
};

// Per-event display labels (used in event cards). Underlying DB values stay
// the same; this only controls how each raw event_type renders.
export const EVENT_TYPE_LABEL = {
  opening: "Opening",
  closing: "Closing",
  workshop: "Workshop",
  lecture: "Lecture / Talk",
  performance: "Performance",
  screening: "Screening",
  tour: "Tour",
  fair: "Other",
  other: "Other",
  exhibition: "Exhibition",
};

// Top-level mode toggle in the header. "events" = one-off events (openings,
// workshops, lectures, etc.); "exhibitions" = current/upcoming exhibitions.
export const MODES = [
  { key: "events", label: "Events" },
  { key: "exhibitions", label: "Exhibitions" },
];

// Sub-selector shown only in Exhibitions mode.
export const EXHIBITION_STATUSES = [
  { key: "current", label: "On view now" },
  { key: "upcoming", label: "Upcoming" },
  { key: "all", label: "All" },
];

// Filter chip groups. Each chip can match multiple raw event_types (e.g.
// Opening/Closing share a chip; "fair" folds into Other). Exhibition is
// intentionally excluded — exhibitions are date ranges, not one-off events,
// so the scraper drops them and the user shouldn't filter on them.
export const EVENT_TYPE_FILTERS = [
  { key: "openingclosing", label: "Opening / Closing", matches: ["opening", "closing"] },
  { key: "workshop", label: "Workshop", matches: ["workshop"] },
  { key: "lecture", label: "Lecture / Talk", matches: ["lecture"] },
  { key: "performance", label: "Performance", matches: ["performance"] },
  { key: "screening", label: "Screening", matches: ["screening"] },
  { key: "tour", label: "Tour", matches: ["tour"] },
  { key: "other", label: "Other", matches: ["other", "fair"] },
];

// A venue counts as "eventful" if it has upcoming events of any of these
// types. Exhibitions alone do not light up a venue — their opening and
// closing receptions do.
export const EVENTFUL_TYPES = new Set([
  "opening", "closing", "workshop", "lecture",
  "performance", "screening", "tour", "fair", "other",
]);

// Date-range presets used by the filter tray. Resolved at filter time so
// "this weekend" tracks the actual current calendar.
export const DATE_PRESETS = [
  { key: "weekend", label: "This weekend" },
  { key: "nextweek", label: "Next week" },
  { key: "month", label: "This month" },
  { key: "all", label: "All dates" },
  { key: "custom", label: "Custom range…" },
];

// Day the public archive started accumulating data. Anything before this is
// surfaced with the "Archive launched on …" notice; nothing exists before it.
ex