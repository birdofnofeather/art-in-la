import React from "react";
import {
  TYPE_COLOR, TYPE_LABEL, REGION_LABEL, EVENT_TYPE_LABEL,
} from "../lib/constants.js";
import { getRelativeLabel, parseDate } from "../lib/filters.js";

const DATE_OPTS  = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
const TIME_OPTS  = { hour: "numeric", minute: "2-digit" };
const DATE_LONG  = { weekday: "long", month: "long", day: "numeric" };

/** Strip any HTML tags that slipped through the scraper pipeline. */
function stripHtml(text) {
  if (!text) return "";
  return text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function fmtDateOnly(d) { return d.toLocaleDateString("en-US", DATE_OPTS); }
function fmtTimeOnly(d) { return d.toLocaleTimeString("en-US", TIME_OPTS); }
function fmtDateTime(d) { return `${fmtDateOnly(d)} · ${fmtTimeOnly(d)}`; }
function fmtGroupLabel(d) { return d.toLocaleDateString("en-US", DATE_LONG); }

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() &&
         a.getMonth()    === b.getMonth()    &&
         a.getDate()     === b.getDate();
}
function hasTime(s) {
  return typeof s === "string" && s.length > 10 && s.includes("T");
}

function dateRange(ev) {
  if (!ev.start) return null;
  const start = new Date(ev.start);
  if (Number.isNaN(+start)) return ev.start;
  const startTimed = hasTime(ev.start) && !ev.all_day;
  const end = ev.end ? new Date(ev.end) : null;
  const endValid = end && !Number.isNaN(+end);
  const endTimed = endValid && hasTime(ev.end) && !ev.all_day;
  if (!endValid || +end === +start) {
    return startTimed ? fmtDateTime(start) : fmtDateOnly(start);
  }
  if (sameDay(start, end)) {
    if (startTimed && endTimed) return `${fmtDateOnly(start)} · ${fmtTimeOnly(start)} – ${fmtTimeOnly(end)}`;
    if (startTimed) return `${fmtDateOnly(start)} · ${fmtTimeOnly(start)}`;
    return fmtDateOnly(start);
  }
  const sameYear = start.getFullYear() === end.getFullYear();
  const startStr = sameYear
    ? start.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
    : fmtDateOnly(start);
  return `${startStr} → ${fmtDateOnly(end)}`;
}

/** Group a sorted array of events into [{dateKey, label, events}] buckets. */
function groupByDate(events) {
  const groups = [];
  const seen = new Map();
  for (const ev of events) {
    const d = parseDate(ev.start);
    const key = d
      ? `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      : "unknown";
    const label = d ? fmtGroupLabel(d) : "Date TBD";
    if (!seen.has(key)) {
      const g = { key, label, events: [] };
      seen.set(key, g);
      groups.push(g);
    }
    seen.get(key).events.push(ev);
  }
  return groups;
}

const LABEL_STYLE = {
  "Now":          "bg-red-500 text-white",
  "Today":        "bg-amber-500 text-white",
  "Tomorrow":     "bg-amber-100 text-amber-800",
  "This weekend": "bg-sky-100 text-sky-800",
  "This week":    "bg-sky-50 text-sky-700",
};

export default function EventList({ events, venuesById, onShowOnMap }) {
  if (events.length === 0) {
    return (
      <div className="panel p-6 text-center text-sm text-ink/60">
        No events match these filters.
      </div>
    );
  }

  const groups = groupByDate(events);

  return (
    <div className="space-y-6">
      {groups.map(({ key, label, events: groupEvents }) => (
        <div key={key}>
          {/* Date group header */}
          <div className="mb-3 flex items-baseline gap-3">
            <h4 className="font-display text-base font-semibold tracking-tight">{label}</h4>
            <span className="text-xs text-ink/40">{groupEvents.length} event{groupEvents.length !== 1 ? "s" : ""}</span>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {groupEvents.map((ev) => {
              const venue = venuesById[ev.venue_id] || { name: ev.venue_id, type: "other" };
              const venueColor = TYPE_COLOR[venue.type] || "#666";
              const relLabel = getRelativeLabel(ev);

              return (
                <article key={ev.id} className="panel overflow-hidden">
                  <div className="h-1 w-full" style={{ background: venueColor }} />
                  <div className="space-y-2 p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="chip" style={{ borderColor: venueColor + "55" }}>
                        <span className="inline-block h-2 w-2 rounded-full" style={{ background: venueColor }} />
                        {TYPE_LABEL[venue.type]}
                      </span>
                      {ev.event_type && (
                        <span className="chip">{EVENT_TYPE_LABEL[ev.event_type] || ev.event_type}</span>
                      )}
                      {venue.region && (
                        <span className="chip">{REGION_LABEL[venue.region] || venue.region}</span>
                      )}
                      {relLabel && (
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${LABEL_STYLE[relLabel] || "bg-ink text-white"}`}>
                          {relLabel}
                        </span>
                      )}
                    </div>

                    <h3 className="font-display text-lg leading-snug">
                      {ev.url ? (
                        <a href={ev.url} target="_blank" rel="noreferrer" className="hover:underline">
                          {ev.title}
                        </a>
                      ) : ev.title}
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
                      {venue.neighborhood && (
                        <span className="text-ink/50"> · {venue.neighborhood}</span>
                      )}
                    </div>

                    {dateRange(ev) && (
                      <div className="text-sm text-ink/70">{dateRange(ev)}</div>
                    )}
                    {ev.description && (
                      <p className="line-clamp-3 text-sm text-ink/70">{stripHtml(ev.description)}</p>
                    )}
                    {ev.artists && ev.artists.length > 0 && (
                      <div className="text-xs text-ink/60">
                        <span className="font-medium">Featuring:</span> {ev.artists.join(", ")}
                      </div>
                    )}

                    {onShowOnMap && venue.lat && (
                      <button
                        type="button"
                        onClick={() => onShowOnMap(ev.venue_id)}
                        className="chip mt-1 text-xs"
                      >
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                        Show on m