import React from "react";
import {
  TYPE_COLOR, TYPE_LABEL, REGION_LABEL, EVENT_TYPE_LABEL,
} from "../lib/constants.js";

const DATE_OPTS = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
const TIME_OPTS = { hour: "numeric", minute: "2-digit" };
const DATE_NO_YEAR = { weekday: "short", month: "short", day: "numeric" };

function fmtDateOnly(d) {
  return d.toLocaleDateString("en-US", DATE_OPTS);
}
function fmtTimeOnly(d) {
  return d.toLocaleTimeString("en-US", TIME_OPTS);
}
function fmtDateTime(d) {
  return `${d.toLocaleDateString("en-US", DATE_OPTS)} · ${fmtTimeOnly(d)}`;
}
function sameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}
function hasTime(s) {
  // ISO strings with time include "T". All-day events stored as a bare date won't.
  return typeof s === "string" && s.length > 10 && s.includes("T");
}

/**
 * Render a date or date range cleanly:
 *   - all-day, no end:               "Sat, May 1, 2026"
 *   - timed, no end:                 "Sat, May 1, 2026 · 7:00 PM"
 *   - same-day, both timed:          "Sat, May 1, 2026 · 7:00 – 9:00 PM"
 *   - cross-day:                     "Mar 13, 2026 → May 9, 2026"
 *     (date-only when ev.all_day or no time-of-day; with time when both timed)
 */
function dateRange(ev) {
  if (!ev.start) return null;
  const start = new Date(ev.start);
  if (Number.isNaN(+start)) return ev.start;

  const startTimed = hasTime(ev.start) && !ev.all_day;
  const end = ev.end ? new Date(ev.end) : null;
  const endValid = end && !Number.isNaN(+end);
  const endTimed = endValid && hasTime(ev.end) && !ev.all_day;

  // No end (or end == start): just one date / datetime.
  if (!endValid || +end === +start) {
    return startTimed ? fmtDateTime(start) : fmtDateOnly(start);
  }

  // Same calendar day: show date once + time range.
  if (sameDay(start, end)) {
    if (startTimed && endTimed) {
      return `${fmtDateOnly(start)} · ${fmtTimeOnly(start)} – ${fmtTimeOnly(end)}`;
    }
    if (startTimed) {
      return `${fmtDateOnly(start)} · ${fmtTimeOnly(start)}`;
    }
    return fmtDateOnly(start);
  }

  // Multi-day range — typical exhibitions. Drop the year on the start if both
  // endpoints share the same year, to read more naturally.
  const sameYear = start.getFullYear() === end.getFullYear();
  const startStr = sameYear
    ? start.toLocaleDateString("en-US", DATE_NO_YEAR)
    : fmtDateOnly(start);
  const endStr = fmtDateOnly(end);
  return `${startStr} → ${endStr}`;
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
