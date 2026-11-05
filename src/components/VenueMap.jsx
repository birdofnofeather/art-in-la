import React, { useMemo, useRef, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import { TYPE_LABEL } from "../lib/constants.js";
import { parseDate } from "../lib/filters.js";
import { LA_COUNTY_GEOJSON } from "../data/laRegions.js";

// Fallback view (centroid of the current venue set); the map auto-fits to the
// actual markers on first load via FitToVenues below.
const CENTER = [34.05, -118.28];
const ZOOM = 10;

const TIME_OPTS = { hour: "numeric", minute: "2-digit" };
const DATE_SHORT = { month: "short", day: "numeric" };

function fmtEventDate(s) {
  const d = parseDate(s);
  if (!d) return "";
  const datePart = d.toLocaleDateString("en-US", DATE_SHORT);
  const hasT = typeof s === "string" && s.includes("T");
  return hasT ? `${datePart} · ${d.toLocaleTimeString("en-US", TIME_OPTS)}` : datePart;
}

const COUNTY_STYLE = {
  color: "#64748b",
  weight: 1.5,
  opacity: 0.45,
  fill: false,
};

// Basemap tiles. CARTO's free basemaps began requiring a paid API key in
// 2026 (every tile rendered "API KEY REQUIRED"), so we use keyless providers:
// OpenStreetMap's standard tiles (muted to a light grey with CSS so the venue
// dots stay the focus), falling back automatically to Esri's light-grey
// canvas if OSM tiles start failing. Neither needs a key or an account.
const TILE_PROVIDERS = [
  {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    className: "tiles-muted",
    maxZoom: 19,
  },
  {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors",
    className: "",
    maxZoom: 16,
  },
];

function BaseTiles() {
  const [idx, setIdx] = React.useState(0);
  const errors = useRef(0);
  const p = TILE_PROVIDERS[idx];
  return (
    <TileLayer
      key={idx}
      url={p.url}
      attribution={p.attribution}
      className={p.className}
      maxZoom={p.maxZoom}
      eventHandlers={{
        tileerror: () => {
          errors.current += 1;
          if (errors.current >= 4 && idx < TILE_PROVIDERS.length - 1) {
            errors.current = 0;
            setIdx(idx + 1);
          }
        },
      }}
    />
  );
}

// Marker colour encodes what a venue offers, matching the filter pills:
//   free  → green (a free upcoming event)     family → blue (a family event)
//   events→ medium grey (other upcoming event) none  → outline only
// Priority when a venue has several: free, then family, then events.
const MARKER = {
  free:   { bg: "#0f7d55", border: "none" },
  family: { bg: "#2f6f9f", border: "none" },
  events: { bg: "#9c9690", border: "none" },
  none:   { bg: "transparent", border: "1.5px solid #1c1917" },
};
function makeIcon(kind, focused = false) {
  const size = 14;
  const m = MARKER[kind] || MARKER.none;
  const ring = focused ? "box-shadow:0 0 0 3px #fff,0 0 0 6px rgba(47,111,159,.4);" : "";
  const html = `<div style="width:${size}px;height:${size}px;border-radius:999px;`
    + `background:${m.bg};border:${m.border};box-sizing:border-box;`
    + `box-shadow:0 0 0 2px #fff,0 1px 3px rgba(28,25,23,.3);${ring}"></div>`;
  return L.divIcon({
    className: "",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  });
}

/** Inner component that reacts to focusedVenueId and flies the map there. */
function FlyController({ venues, focusedVenueId, markerRefs }) {
  const map = useMap();
  const prevId = useRef(null);

  useEffect(() => {
    if (!focusedVenueId || focusedVenueId === prevId.current) return;
    prevId.current = focusedVenueId;
    const v = venues.find((x) => x.id === focusedVenueId);
    if (!v || typeof v.lat !== "number") return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    map.flyTo([v.lat, v.lng], Math.max(map.getZoom(), 15), {
      duration: reduce ? 0 : 0.7,
      animate: !reduce,
    });
    // Open popup after animation
    const t = setTimeout(() => {
      const marker = markerRefs.current[focusedVenueId];
      if (marker) marker.openPopup();
    }, 800);
    return () => clearTimeout(t);
  }, [focusedVenueId, map, venues, markerRefs]);

  return null;
}

/** Frame the visible venues. Runs on load and whenever the set of visible
    venues changes (filters). Far-flung outliers (Lancaster, Catalina) are left
    out of the frame so the core cluster fills the map; they stay reachable by
    zooming out. Skipped while a venue is focused (FlyController owns the
    camera then). */
export function frameBounds(points) {
  if (points.length === 0) return null;
  if (points.length <= 3) return L.latLngBounds(points);
  const med = (arr) => { const a = [...arr].sort((x, y) => x - y); return a[Math.floor(a.length / 2)]; };
  const cLat = med(points.map((p) => p[0]));
  const cLng = med(points.map((p) => p[1]));
  const dist = points.map((p) => Math.hypot(p[0] - cLat, (p[1] - cLng) * 0.83));
  const cutoff = Math.max(med(dist) * 4, 0.15);
  const core = points.filter((_, i) => dist[i] <= cutoff);
  return L.latLngBounds(core.length >= 2 ? core : points);
}

function FitToVenues({ mappable, focusedVenueId }) {
  const map = useMap();
  const lastKey = useRef("");
  useEffect(() => {
    if (focusedVenueId || mappable.length === 0) return;
    const key = mappable.map((v) => v.id).sort().join(",");
    if (key === lastKey.current) return;
    lastKey.current = key;
    const b = frameBounds(mappable.map((v) => [v.lat, v.lng]));
    if (b) map.fitBounds(b, { padding: [28, 28], maxZoom: mappable.length < 4 ? 12 : 14 });
  }, [map, mappable, focusedVenueId]);
  return null;
}

export default function VenueMap({
  venues, eventfulIds,
  onlyEventful, setOnlyEventful,
  upcomingEvents,
  focusedVenueId,
  onShowDetail,
  onGoToEvents,
}) {
  const iconCache = useMemo(() => new Map(), []);
  const markerRefs = useRef({});

  const kindFor = (v) => {
    const evs = eventsByVenue.get(v.id) || [];
    if (evs.some((e) => e.is_free === true)) return "free";
    if (evs.some((e) => (e.audience || []).includes("family"))) return "family";
    if (evs.length > 0 || eventfulIds.has(v.id)) return "events";
    return "none";
  };
  const iconFor = (v) => {
    const kind = kindFor(v);
    const focused = v.id === focusedVenueId;
    const key = `${kind}|${focused ? 1 : 0}`;
    if (!iconCache.has(key)) iconCache.set(key, makeIcon(kind, focused));
    return iconCache.get(key);
  };

  // Group upcoming events by venue_id for popup lookup
  const eventsByVenue = useMemo(() => {
    const map = new Map();
    for (const ev of (upcomingEvents || [])) {
      if (!map.has(ev.venue_id)) map.set(ev.venue_id, []);
      map.get(ev.venue_id).push(ev);
    }
    return map;
  }, [upcomingEvents]);

  const mappable = useMemo(
    () => venues.filter((v) => typeof v.lat === "number" && typeof v.lng === "number"),
    [venues]
  );

  const dot = (bg, border) => (
    <span className="inline-block h-3 w-3 rounded-full" style={{ background: bg, border, boxSizing: "border-box" }} />
  );

  return (
    <div className="panel overflow-hidden">
      {/* Controls above the map: toggle (left) · key (right) */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink/10 px-4 py-2.5 text-xs text-ink/70">
        <label className="inline-flex cursor-pointer items-center gap-2 select-none">
          <button
            type="button"
            onClick={() => setOnlyEventful(!onlyEventful)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 ${onlyEventful ? "bg-accent" : "bg-ink/20"}`}
            aria-pressed={onlyEventful}
            aria-label={onlyEventful ? "Showing venues with events only" : "Showing all venues"}
          >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${onlyEventful ? "translate-x-[18px]" : "translate-x-0.5"}`} />
          </button>
          <span>{onlyEventful ? "Venues with events" : "All venues"}</span>
        </label>

        <div className="ml-auto flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="inline-flex items-center gap-1.5">{dot("#0f7d55")} Free</span>
          <span className="inline-flex items-center gap-1.5">{dot("#2f6f9f")} Family</span>
          <span className="inline-flex items-center gap-1.5">{dot("#9c9690")} Events</span>
          <span className="inline-flex items-center gap-1.5">{dot("transparent", "1.5px solid #1c1917")} No events</span>
        </div>
      </div>

      <MapContainer
        center={CENTER}
        zoom={ZOOM}
        scrollWheelZoom
        zoomSnap={0.25}
        zoomDelta={0.5}
        style={{ height: "min(68vh, 600px)", minHeight: 360, width: "100%" }}
      >
        <BaseTiles />
        {/* County outline only — the old rectangular region boxes read as
            map errors over real streets; regions remain a filter. */}
        <GeoJSON key="county" data={LA_COUNTY_GEOJSON} style={COUNTY_STYLE} interactive={false} />

        <FlyController venues={venues} focusedVenueId={focusedVenueId} markerRefs={markerRefs} />
        <FitToVenues mappable={mappable} focusedVenueId={focusedVenueId} />
        {mappable.map((v) => {
          const vEvents = eventsByVenue.get(v.id) || [];
          const nextEvents = vEvents.slice(0, 3);
          return (
            <Marker
              key={v.id}
              position={[v.lat, v.lng]}
              icon={iconFor(v)}
              ref={(el) => { if (el) markerRefs.current[v.id] = el; }}
            >
              <Popup>
                <div className="space-y-1.5" style={{ minWidth: 180 }}>
                  <div className="font-semibold text-sm">{v.name}</div>
                  <div className="text-xs text-ink/60">
                    {v.neighborhood || TYPE_LABEL[v.type]}
                  </div>
                  {v.description && (
                    <div className="text-xs text-ink/70 line-clamp-2">{v.description}</div>
                  )}

                  {nextEvents.length > 0 && (
                    <div className="border-t border-black/10 pt-1.5 mt-1.5 space-y-1">
                      {nextEvents.map((ev) => (
                        <div key={ev.id} className="text-xs">
                          <div className="font-medium leading-snug line-clamp-1">
                            {ev.url ? <a href={ev.url} target="_blank" rel="noreferrer" className="hover:underline">{ev.title}</a> : ev.title}
                          </div>
                          <div className="text-ink/60">
                            {ev.start ? fmtEventDate(ev.start) : ""}
                            {ev.is_free === true && <span className="ml-1 font-semibold text-emerald-700">Free</span>}
                            {(ev.audience || []).includes("family") && <span className="ml-1 font-semibold text-sky-700">Family</span>}
                          </div>
                        </div>
                      ))}
                      {vEvents.length > 3 && (
                        <div className="text-xs text-ink/60">+{vEvents.length - 3} more</div>
                      )}
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5 pt-1 text-xs border-t border-black/10 mt-1">
                    {v.website && (
                      <a href={v.website} target="_blank" rel="noreferrer" className="underline text-ink/60">Website</a>
                    )}
                    {v.events_url && (
                      <a href={v.events_url} target="_blank" rel="noreferrer" className="underline text-ink/60">Events</a>
                    )}
                    {v.address && (
                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(v.address)}`}
                        target="_blank" rel="noreferrer" className="underline text-ink/60"
                      >Directions</a>
                    )}
                    {onShowDetail && (
                      <button type="button" onClick={() => onShowDetail(v.id)} className="underline text-ink/60">Details</button>
                    )}
                    {onGoToEvents && vEvents.length > 0 && (
                      <button type="button" onClick={() => onGoToEvents(v.id)} className="underline text-ink/60">
                        See events →
                      </button>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
