import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { TYPE_COLOR, TYPE_LABEL, TYPE_LETTER } from "../lib/constants.js";

// LA County rough center + zoom
const CENTER = [34.05, -118.35];
const ZOOM = 10;

function makeIcon(type, eventful) {
  const color = TYPE_COLOR[type] || "#333";
  const letter = TYPE_LETTER[type] || "?";
  return L.divIcon({
    className: `custom-marker ${eventful ? "event" : ""}`,
    html: `<div class="custom-marker ${eventful ? "event" : ""}" style="background:${color}">${letter}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
}

export default function VenueMap({ venues, eventfulIds, onlyEventful, setOnlyEventful }) {
  // Avoid recreating icons for every render
  const iconCache = useMemo(() => new Map(), []);
  const iconFor = (v) => {
    const eventful = eventfulIds.has(v.id);
    const key = `${v.type}|${eventful ? 1 : 0}`;
    if (!iconCache.has(key)) iconCache.set(key, makeIcon(v.type, eventful));
    return iconCache.get(key);
  };

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
        {venues
          .filter((v) => typeof v.lat === "number" && typeof v.lng === "number")
          .map((v) => (
            <Marker key={v.id} position={[v.lat, v.lng]} icon={iconFor(v)}>
              <Popup>
                <div className="space-y-1">
                  <div className="font-semibold">{v.name}</div>
                  <div className="text-xs text-ink/60">
                    {TYPE_LABEL[v.type]} · {v.neighborhood}
                    {eventfulIds.has(v.id) && (
                      <span className="ml-1 inline-block h-2 w-2 rounded-full bg-amber-500 align-middle" />
                    )}
                  </div>
                  <div className="text-sm">{v.description}</div>
                  <div className="flex flex-wrap gap-2 pt-1 text-xs">
                    {v.website && (
                      <a href={v.website} target="_blank" rel="noreferrer" className="underline">
                        Website
                      </a>
                    )}
                    {v.events_url && (
                      <a href={v.events_url} target="_blank" rel="noreferrer" className="underline">
                        Events
                      </a>
                    )}
                    {v.address && (
                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(v.address)}`}
                        target="_blank"
                        rel="noreferrer"
                        className="underline"
                      >
                        Directions
                      </a>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-xs text-ink/60">
        <span className="font-semibold uppercase tracking-wider">Legend</span>
        {Object.entries(TYPE_LABEL).map(([k, label]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ background: TYPE_COLOR[k] }}
            />
            {label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-full bg-amber-500" />
          Has upcoming event
        </span>
        {/* Filter toggle */}
        <label className="ml-auto inline-flex cursor-pointer items-center gap-2 select-none">
          <span>{onlyEventful ? "Showing venues with events" : "Showing all venues"}</span>
          <button
            type="button"
            onClick={() => setOnlyEventful(!onlyEventful)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              onlyEventful ? "bg-amber-500" : "bg-ink/20"
            }`}
            aria-pressed={onlyEventful}
            aria-label="Show only venues with upcoming events"
          >
            <span
              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                onlyEventful ? "translate-x-4.5" : "translate-x-0.5"
              }`}
            />
          </button>
        </label>
      </div>
    </div>
  );
}
