import React, { useEffect, useRef, useState } from "react";
import {
  TYPE_COLOR, TYPE_LABEL, REGION_LABEL, EVENT_TYPE_LABEL,
} from "../lib/constants.js";
import { getRelativeLabel, parseDate, eventTypesOf, isExhibition } from "../lib/filters.js";
import { downloadICS, googleCalUrl } from "../lib/calendar.js";

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
  const start = parseDate(ev.start);
  if (!start) return ev.start;
  const startTimed = hasTime(ev.start) && !ev.all_day;
  const end = ev.end ? parseDate(ev.end) : null;
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

const startMs = (ev) => parseDate(ev.start)?.getTime() ?? Infinity;

/**
 * Order a single day's events so each organization's cards sit together
 * (invisible grouping — no venue header) while the day still reads
 * chronologically: venue blocks are ordered by their earliest start, and
 * within a block events are sorted by start time.
 */
function orderWithinDay(events) {
  const earliest = new Map();
  for (const ev of events) {
    const t = startMs(ev);
    if (t < (earliest.get(ev.venue_id) ?? Infinity)) earliest.set(ev.venue_id, t);
  }
  return [...events].sort((a, b) => {
    const ea = earliest.get(a.venue_id) ?? Infinity;
    const eb = earliest.get(b.venue_id) ?? Infinity;
    if (ea !== eb) return ea - eb;                       // venue blocks, chronological
    if (a.venue_id !== b.venue_id)                        // stable tiebreak for same earliest
      return a.venue_id < b.venue_id ? -1 : 1;
    return startMs(a) - startMs(b);                       // within a venue, by start time
  });
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
  for (const g of groups) g.events = orderWithinDay(g.events);
  return groups;
}

const LABEL_STYLE = {
  "Now":          "bg-red-500 text-white",
  "Today":        "bg-amber-500 text-white",
  "Tomorrow":     "bg-amber-100 text-amber-800",
  "This weekend": "bg-sky-100 text-sky-800",
  "This week":    "bg-sky-50 text-sky-700",
};

/** Days until an exhibition closes, or null if no usable end date. */
function daysUntilClose(ev, now = new Date()) {
  const end = parseDate(ev.end);
  if (!end) return null;
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((end - today0) / 864e5);
}

// ── Calendar icon (10×10, matching map-pin style) ───────────────────────────
const CalIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0">
    <rect x="3" y="4" width="18" height="18" rx="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

/**
 * Single "Add to calendar" chip that opens a small popover offering the two
 * destinations: an .ics download (Apple Calendar / Outlook) and a Google
 * Calendar link. Closes on selection, outside click, or Escape.
 */
function CalendarMenu({ ev, venue }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const gCalUrl = ev.start ? googleCalUrl(ev, venue) : null;

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const itemClass =
    "block w-full rounded px-3 py-1.5 text-left text-xs hover:bg-black/5 " +
    "focus-visible:outline-none focus-visible:bg-black/5";

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="chip text-xs"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <CalIcon /> Add to calendar
      </button>
      {open && (
        <div
          role="menu"
          className="absolute left-0 bottom-full z-20 mb-1 w-44 rounded-lg border border-black/10 bg-white p-1 shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => { downloadICS(ev, venue); setOpen(false); }}
            className={itemClass}
          >
            iCalendar / Outlook
          </button>
          {gCalUrl && (
            <a
              role="menuitem"
              href={gCalUrl}
              target="_blank"
              rel="noreferrer"
              onClick={() => setOpen(false)}
              className={itemClass}
            >
              Google Calendar
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function EventCard({ ev, venuesById, onShowOnMap, isFav, onToggleFav }) {
  const venue = venuesById[ev.venue_id] || { name: ev.venue_id, type: "other" };
  const venueColor = TYPE_COLOR[venue.type] || "#666";
  const exhibition = isExhibition(ev);
  const relLabel = exhibition ? null : getRelativeLabel(ev);
  const closeIn = exhibition ? daysUntilClose(ev) : null;
  const closingSoon = closeIn !== null && closeIn >= 0 && closeIn <= 14;
  // De-duplicate type chips by their display label (e.g. fair + other → one "Other").
  const typeLabels = [...new Set(
    eventTypesOf(ev).map((t) => EVENT_TYPE_LABEL[t] || t)
  )];

  return (
    <article className="panel flex overflow-hidden">
      <div className="w-1 shrink-0" style={{ background: venueColor }} />
      {ev.image && (
        <img
          src={ev.image}
          alt=""
          loading="lazy"
          className="hidden h-auto w-28 shrink-0 object-cover sm:block"
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
      )}
      <div className="relative min-w-0 flex-1 space-y-2 p-4">
        {/* Star / save button */}
        {onToggleFav && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onToggleFav(); }}
            className={`absolute right-2 top-2 p-1 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 ${
              isFav ? "text-amber-500" : "text-ink/25 hover:text-amber-400"
            }`}
            aria-label={isFav ? "Remove from saved" : "Save event"}
          >
            {isFav ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            )}
          </button>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs pr-6">
          <span className="chip" style={{ borderColor: venueColor + "55" }}>
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: venueColor }} />
            {TYPE_LABEL[venue.type]}
          </span>
          {typeLabels.map((label) => (
            <span key={label} className="chip">{label}</span>
          ))}
          {venue.region && (
            <span className="chip">{REGION_LABEL[venue.region] || venue.region}</span>
          )}
          {relLabel && (
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${LABEL_STYLE[relLabel] || "bg-ink text-white"}`}>
              {relLabel}
            </span>
          )}
          {closingSoon && (
            <span className="inline-flex items-center rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold text-white">
              {closeIn === 0 ? "Closes today" : closeIn === 1 ? "Closes tomorrow" : `Closes in ${closeIn} days`}
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

        {/* Action row */}
        <div className="flex flex-wrap gap-1.5 mt-1">
          {onShowOnMap && venue.lat && (
            <button
              type="button"
              onClick={() => onShowOnMap(ev.venue_id)}
              className="chip text-xs"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
              Show on map
            </button>
          )}
          {ev.start && !exhibition && <CalendarMenu ev={ev} venue={venue} />}
        </div>
      </div>
    </article>
  );
}

/**
 * `grouped` (default true): bucket events under date headers by start date —
 * right for one-off events and the archive. Exhibitions pass grouped=false to
 * render a single flat grid in the order given (sorted by closing date), since
 * grouping by start date would scatter the ending-soonest ordering.
 */
export default function EventList({ events, venuesById, onShowOnMap, onReset, grouped = true, favs, onToggleFav }) {
  if (events.length === 0) {
    return (
      <div className="panel space-y-3 p-6 text-center text-sm text-ink/60">
        <div>No events match these filters.</div>
        {onReset && (
          <button type="button" onClick={onReset} className="chip">Clear filters & search</button>
        )}
      </div>
    );
  }

  const renderCard = (ev) => (
    <EventCard
      key={ev.id}
      ev={ev}
      venuesById={venuesById}
      onShowOnMap={onShowOnMap}
      isFav={favs?.has(ev.id) ?? false}
      onToggleFav={onToggleFav ? () => onToggleFav(ev.id) : null}
    />
  );

  if (!grouped) {
    return (
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {events.map(renderCard)}
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
            {groupEvents.map(renderCard)}
          </div>
        </div>
      ))}
    </div>
  );
}
