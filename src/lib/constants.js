// Shared taxonomy and UI constants.

// Art vs. performing arts. Every venue in venues.json carries exactly one
// `discipline`, assigned by its PRIMARY facility and core programme:
//   visual     — its core programme is exhibiting art (museums, galleries,
//                art centers). Its talks, screenings and concerts still count.
//   performing — its main facility is a stage/auditorium and its core
//                programme is live performance (music, theater, dance,
//                spoken word).
export const DISCIPLINES = [
  { key: "visual",     label: "Art",             long: "Art venues" },
  { key: "performing", label: "Performing arts", long: "Performing arts venues" },
  { key: "all",        label: "All",             long: "All venues" },
];
export const DEFAULT_DISCIPLINE = "visual";

export const TYPE_LABEL = {
  museum: "Museum",
  community: "Community",
  alternative: "Alternative",
  academic: "Academic",
  theater: "Theater",
  music: "Music & opera",
  center: "Performing arts center",
};

export const TYPE_COLOR = {
  museum: "#0f172a",
  community: "#15803d",
  alternative: "#7c3aed",
  academic: "#b45309",
  theater: "#9f1239",
  music: "#1d4ed8",
  center: "#0f766e",
};

export const TYPE_LETTER = {
  museum: "M",
  community: "C",
  alternative: "X",
  academic: "A",
};

// Short, plain-language definition of each organization type — surfaced as a
// tooltip on the filter buttons. Cross-referenced against how the museum field
// and LA art guides describe these categories.
export const TYPE_DEF = {
  museum: "Established nonprofit museums — permanent collections or major exhibition programs.",
  community: "Neighborhood cultural centers and nonprofits rooted in a specific community.",
  alternative: "Artist-run, experimental, noncommercial project spaces.",
  academic: "Galleries, museums and stages based at a university, college, or art school.",
  theater: "Nonprofit theater companies and playhouses.",
  music: "Orchestras and opera companies at their home halls.",
  center: "Performing arts centers presenting music, dance, and theater.",
};

export const REGION_LABEL = {
  westside: "Westside",
  central: "Central / Mid-City",
  downtown: "Downtown / DTLA",
  eastside: "Eastside / NELA",
  pasadena: "Pasadena / Foothills",
  valley: "San Fernando Valley",
  south: "South LA",
  southbay: "South Bay / Long Beach",
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
  { key: "today", label: "Today" },
  { key: "weekend", label: "This weekend" },
  { key: "nextweekend", label: "Next weekend" },
  { key: "next7", label: "Next 7 days" },
  { key: "all", label: "Any date" },
];

// All presets render as one always-visible chip row.
export const PRIMARY_DATE_PRESETS = ["today", "weekend", "nextweekend", "next7", "all"];

// Day the public archive started accumulating data. Anything before this is
// surfaced with the "Archive launched on …" notice; nothing exists before it.
export const ARCHIVE_LAUNCH_DATE = "2026-04-25";
