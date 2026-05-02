import React, { useMemo, useRef, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { TYPE_COLOR, TYPE_LABEL } from "../lib/constants.js";
import { parseDate } from "../lib/filters.js";

const CENTER = [34.05, -118.35];
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

function makeIcon(type, eventful) {
  const color = TYPE_COLOR[type] || "#333";
  const letter = (type || "").charAt(0).toUpperCase() || "?";
  return L.divIcon({
    className: "",
    html: `<div class="custom-marker ${eventful ? "event" : ""}" style="background:${color}">${letter}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
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
    map.flyTo([v.lat, v.lng], Math.max(map.getZoom(), 15), { duration: 0.7 });
    // Open popup after animation
    const t = setTimeout(() => {
      const marker = markerRefs.current[focusedVenueId];
      if (marker) marker.openPopup();
    }, 800);
    return () => clearTimeout(t);
  }, [focusedVenueId, map, venues, markerRefs]);

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

  const iconFor = (v) => {
    const eventful = eventfulIds.has(v.id);
    const key = `${v.type}|${eventful ? 1 : 0}`;
    if (!iconCache.has(key)) iconCache.set(key, makeIcon(v.type, eventful));
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

  return (
    <div className="panel overflow-hidden">
      <MapContainer
        center={CENTER}
        zoom={ZOOM}
        scrollWheelZoom
        style={{ height: "560px", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &middot; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <FlyController venues={venues} focusedVenueId={focusedVenueId} markerRefs={markerRefs} />
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
                    {TYPE_LABEL[v.type]} · {v.neighborhood}
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
                          {ev.start && <div className="text-ink/50">{fmtEventDate(ev.start)}</div>}
                        </div>
                      ))}
                      {vEvents.length > 3 && (
                        <div className="text-xs text-ink/40">+{vEvents.length - 3} more</div>
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

      {/* Legend + toggle */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-xs text-ink/60">
        <span className="font-semibold uppercase tracking-wider">Legend</span>
        {Object.entries(TYPE_LABEL).map(([k, label]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full" style={{ background: TYPE_COLOR[k] }} />
            {label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-full bg-amber-500" />
          Has upcoming event
        </span>

        <label className="ml-auto inline-flex cursor-pointer items-center gap-2 select-none">
          <span>{onlyEventful ? "Events only" : "All venues"}</span>
          <button
            type="button"
            onClick={() => setOnlyEventful(!onlyEventful)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${onlyEventful ? "bg-amber-500" : "bg-ink/20"}`}
            aria-pressed={onlyEventful}
          >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${onlyEventful ? "translate-x-[18px]" : "translate-x-0.5"}`} />
          </button>
        </label>
      </div>
    </div>
  );
}
