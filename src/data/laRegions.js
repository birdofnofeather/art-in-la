// Approximate LA County outline and informal region polygons for the venue map.
// Coordinates are [longitude, latitude] per GeoJSON spec.
// Polygons are intentionally simplified — these are informal zones, not
// official administrative boundaries.

/** Simplified LA County boundary polygon. */
export const LA_COUNTY_GEOJSON = {
  type: "Feature",
  geometry: {
    type: "Polygon",
    coordinates: [[
      [-119.05, 34.08], // Coast — Ventura/LA border near Point Mugu
      [-119.05, 34.55], // North along Ventura border
      [-118.95, 34.82], // LA/Ventura/Kern corner (NW Antelope Valley)
      [-118.40, 34.82], // Northern Antelope Valley
      [-118.00, 34.65], // NE Antelope Valley
      [-117.73, 34.60], // LA/San Bernardino border (high desert)
      [-117.65, 34.08], // LA/SB/OC border area
      [-117.65, 33.86], // Southeast corner
      [-117.95, 33.74], // Along OC border
      [-118.07, 33.70], // Coast — Long Beach / Seal Beach
      [-118.27, 33.70], // San Pedro
      [-118.40, 33.76], // Palos Verdes
      [-118.52, 34.00], // Santa Monica / Malibu coast
      [-119.05, 34.08], // Close polygon
    ]],
  },
};

// Each region: id, short label for the map, centroid [lat, lng], polygon coords [lng, lat]
const REGIONS_RAW = [
  {
    id: "valley",
    label: "Valley",
    centroid: [34.30, -118.60],
    coords: [
      [-119.0, 34.14], [-118.18, 34.14], [-118.18, 34.55],
      [-119.0, 34.55], [-119.0, 34.14],
    ],
  },
  {
    id: "antelope",
    label: "Antelope Valley",
    centroid: [34.68, -118.20],
    coords: [
      [-118.75, 34.52], [-117.65, 34.52], [-117.65, 34.83],
      [-118.75, 34.83], [-118.75, 34.52],
    ],
  },
  {
    id: "northeast",
    label: "Northeast",
    centroid: [34.16, -118.24],
    coords: [
      [-118.32, 34.09], [-118.13, 34.09], [-118.13, 34.23],
      [-118.32, 34.23], [-118.32, 34.09],
    ],
  },
  {
    id: "pasadena",
    label: "Pasadena",
    centroid: [34.14, -117.97],
    coords: [
      [-118.18, 34.07], [-117.63, 34.07], [-117.63, 34.23],
      [-118.18, 34.23], [-118.18, 34.07],
    ],
  },
  {
    id: "westside",
    label: "Westside",
    centroid: [34.05, -118.53],
    coords: [
      [-119.0, 33.91], [-118.37, 33.91], [-118.37, 34.19],
      [-119.0, 34.19], [-119.0, 33.91],
    ],
  },
  {
    id: "central",
    label: "Central",
    centroid: [34.10, -118.33],
    coords: [
      [-118.40, 34.02], [-118.22, 34.02], [-118.22, 34.18],
      [-118.40, 34.18], [-118.40, 34.02],
    ],
  },
  {
    id: "downtown",
    label: "Downtown",
    centroid: [34.044, -118.243],
    coords: [
      [-118.28, 33.99], [-118.19, 33.99], [-118.19, 34.08],
      [-118.28, 34.08], [-118.28, 33.99],
    ],
  },
  {
    id: "eastside",
    label: "Eastside",
    centroid: [34.09, -118.16],
    coords: [
      [-118.27, 34.01], [-118.04, 34.01], [-118.04, 34.18],
      [-118.27, 34.18], [-118.27, 34.01],
    ],
  },
  {
    id: "south",
    label: "South LA",
    centroid: [33.97, -118.29],
    coords: [
      [-118.40, 33.92], [-118.15, 33.92], [-118.15, 34.03],
      [-118.40, 34.03], [-118.40, 33.92],
    ],
  },
  {
    id: "southbay",
    label: "South Bay",
    centroid: [33.82, -118.37],
    coords: [
      [-118.55, 33.70], [-118.20, 33.70], [-118.20, 33.93],
      [-118.55, 33.93], [-118.55, 33.70],
    ],
  },
  {
    id: "longbeach",
    label: "Long Beach",
    centroid: [33.77, -118.18],
    coords: [
      [-118.28, 33.68], [-118.05, 33.68], [-118.05, 33.88],
      [-118.28, 33.88], [-118.28, 33.68],
    ],
  },
];

/** GeoJSON FeatureCollection with all region polygons. */
export const REGIONS_GEOJSON = {
  type: "FeatureCollection",
  features: REGIONS_RAW.map(({ id, label, coords }) => ({
    type: "Feature",
    properties: { id, label },
    geometry: { type: "Polygon", coordinates: [coords] },
  })),
};

/** Label anchor points: { id, label, lat, lng } */
export const REGION_LABELS = REGIONS_RAW.map(({ id, label, centroid }) => ({
  id,
  label,
  lat: centroid[0],
  lng: centroid[1],
}));
