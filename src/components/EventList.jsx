import React from "react";
import {
  TYPE_COLOR, TYPE_LABEL, REGION_LABEL, EVENT_TYPE_LABEL,
} from "../lib/constants.js";

function fmtDate(s, { dateOnly = false } = {}) {
  if (!s) return null;
  const d = new Date(s);
  if (Number.isNaN(+d)) return s;
  const datePart = d.toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
  });
  if (dateOnly || s.length <= 10) return datePart;
  const timePart = d.toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit",
  });
  return `${datePart} · ${timePart}`;
}

function dateRange(ev) {
  if (!ev.start) return null;
  const first = fmtDate(ev.start, { dateOnly: ev.all_day });
  if (!ev.end || ev.end === ev.start) return first;
  return `${first} → ${fmtDate(ev.end, { dateOnly: ev.all_day })}`;
}

export default function EventList({ events, venuesById }) {
  if (events.length === 0) {
    return (
      <div className="panel p-6 text-center text-sm text-ink/60">
        No events match these filters.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {events.map((ev) => {
        const venue = venuesById[ev.venue_id] || { name: ev.venue_id, type: "other" };
        const venueColor = TYPE_COLOR[venue.type] || "#666";
        return (
          <article key={ev.id} className="panel overflow-hidden">
            <div className="h-1 w-full" style={{ background: venueColor }} />
            <div className="space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="chip" style={{ borderColor: venueColor + "55" }}>
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: venueColor }}
                  />
                  {TYPE_LABEL[venue.type]}
                </span>
                {ev.event_type && (
                  <span className="chip">{EVENT_TYPE_LABEL[ev.event_type] || ev.event_type}</span>
                )}
                {venue.region && (
                  <span className="chip">{REGION_LABEL[venue.region] || venue.region}</span>
                )}
              </div>
              <h3 className="font-display text-lg leading-snug">
                {ev.url ? (
                  <a href={ev.url} target="_blank" rel="noreferrer" className="hover:underline">
                    {ev.title}
                  </a>
                ) : (
                  ev.title
                )}
              </h3>
              <div className="text-sm text-ink/70">
                <a
                  href={venue.website || "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium underline-offset-2 hover:underline"
                >
                  {venue.name}
                </a>
                {venue.neighborhood && <span className="text-ink/50"> · {venue.neighborhood}</span>}
              </div>
              {dateRange(ev) && (
                <div className="text-sm text-ink/70">{dateRange(ev)}</div>
              )}
              {ev.description && (
                <p className="line-clamp-3 text-sm text-ink/70">{ev.description}</p>
              )}
              {ev.artists && ev.artists.length > 0 && (
                <div className="text-xs text-ink/60">
                  <span className="font-medium">Featuring:</span> {ev.artists.join(", ")}
                </div>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
