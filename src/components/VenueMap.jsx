import React, { useMemo, useRef, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import { TYPE_LABEL } from "../lib/constants.js";
import { parseDate } from "../lib/filters.js";
import { LA_COUNTY_GEOJSON, REGIONS_GEOJSON, REGION_LABELS } from "../data/laRegions.js";

// Fallback view (centroid of the current venue set); the map auto-fits to the
// actual markers on first load via FitBoundsOnce below.
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

const REGION_STYLE = {
  color: "#94a3b8",
  weight: 0.8,
  opacity: 0.5,
  fillColor: "#94a3b8",
  fillOpacity: 0.05,
};

function makeLabelIcon(text) {
  return L.divIcon({
    className: "region-label",
    html: `<span>${text}</span>`,
    iconSize: [130, 18],
    iconAnchor: [65, 9],
  });
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

/** Fit the map to the venue markers once, on first load — keeps the view
    centered on whatever the current venue set actually covers. Skipped when a
    venue is being focused (FlyController owns the camera then). */
function FitBoundsOnce({ mappable, focusedVenueId }) {
  const map = useMap();
  const done = useRef(false);

  useEffect(() => {
    if (done.current || focusedVenueId || mappable.length === 0) return;
    done.current = true;
    // Default view: the core of LA where most venues sit — roughly Burbank
    // down to Long Beach — instead of zooming out to fit Lancaster.
    const CORE = L.latLngBounds([33.73, -118.56], [34.20, -118.10]);
    map.fitBounds(CORE, { maxZoom: 12 });
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
        style={{ height: "min(70vh, 560px)", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &middot; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {/* Region fills + county outline */}
        <GeoJSON key="regions" data={REGIONS_GEOJSON} style={REGION_STYLE} interactive={false} />
        <GeoJSON key="county" data={LA_COUNTY_GEOJSON} style={COUNTY_STYLE} interactive={false} />

        {/* Region text labels at centroid */}
        {REGION_LABELS.map(({ id, label, lat, lng }) => (
          <Marker
            key={`rl-${id}`}
            position={[lat, lng]}
            icon={makeLabelIcon(label)}
            interactive={false}
            keyboard={false}
            zIndexOffset={-1000}
          />
        ))}

        <FlyController venues={venues} focusedVenueId={focusedVenueId} markerRefs={markerRefs} />
        <FitBoundsOnce mappable={mappable} focusedVenueId={focusedVenueId} />
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
