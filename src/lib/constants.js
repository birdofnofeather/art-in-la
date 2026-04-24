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
  alternative: "A",
  academic: "U",
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

export const EVENT_TYPE_LABEL = {
  opening: "Opening",
  closing: "Closing",
  exhibition: "Exhibition",
  workshop: "Workshop",
  lecture: "Lecture / Talk",
  performance: "Performance",
  screening: "Screening",
  tour: "Tour",
  fair: "Fair",
  other: "Other",
};

// A venue counts as "eventful" for the map toggle if it has upcoming events
// of any of these types (exhibitions alone do not light up a venue — their
// opening and closing receptions do).
export const EVENTFUL_TYPES = new Set([
  "opening", "closing", "workshop", "lecture",
  "performance", "screening", "tour", "fair", "other",
]);
