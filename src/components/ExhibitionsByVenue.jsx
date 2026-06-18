import React from "react";
import { TYPE_COLOR, TYPE_LABEL, REGION_LABEL } from "../lib/constants.js";
import { parseDate } from "../lib/filters.js";

const DATE_OPTS = { month: "short", day: "numeric" };
const DATE_OPTS_Y = { month: "short", day: "numeric", year: "numeric" };

function fmtRange(ev) {
  const s = parseDate(ev.start);
  const e = parseDate(ev.end);
  if (!s) return null;
  if (!e || +e === +s) return s.toLocaleDateString("en-US", DATE_OPTS_Y);
  const sameYear = s.getFullYear() === e.getFullYear();
  const sStr = s.toLocaleDateString("en-US", sameYear ? DATE_OPTS : DATE_OPTS_Y);
  return `${sStr} – ${e.toLocaleDateString("en-US", DATE_OPTS_Y)}`;
}

function daysUntilClose(ev, now = new Date()) {
  const end = parseDate(ev.end);
  if (!end) return null;
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((end - today0) / 864e5);
}

function StarButton({ isFav, onToggle, label }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      className={`shrink-0 rounded p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 ${
        isFav ? "text-amber-500" : "text-ink/25 hover:text-amber-400"
      }`}
      aria-label={label}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill={isFav ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
      </svg>
    </button>
  );
}

/**
 * Exhibitions grouped by organization: one card per venue, each listing that
 * venue's on-view exhibitions (linked, with dates). No "add to calendar" — a
 * months-long show isn't a calendar entry. Venues are ordered by their
 * soonest-closing show; the incoming list is already ending-soonest first.
 */
export default function ExhibitionsByVenue({
  exhibitions, venuesById, onShowDetail, onReset, favs, onToggleFav,
}) {
  if (!exhibitions || exhibitions.length === 0) {
    return (
      <div className="panel space-y-3 p-6 text-center text-sm text-ink/60">
        <div>No exhibitions match these filters.</div>
        {onReset && (
          <button type="button" onClick={onReset} className="chip">Clear filters &amp; search</button>
        )}
      </div>
    );
  }

  // Group by venue, preserving the ending-soonest order of first appearance.
  const order = [];
  const byVenue = new Map();
  for (const ev of exhibitions) {
    if (!byVenue.has(ev.venue_id)) {
      byVenue.set(ev.venue_id, []);
      order.push(ev.venue_id);
    }
    byVenue.get(ev.venue_id).push(ev);
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {order.map((venueId) => {
        const venue = venuesById[venueId] || { name: venueId, type: "other" };
        const color = TYPE_COLOR[venue.type] || "#666";
        const shows = byVenue.get(venueId);
        return (
          <article key={venueId} className="panel overflow-hidden">
            <div className="h-1 w-full" style={{ background: color }} />
            <div className="space-y-3 p-4">
              {/* Org header */}
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="chip" style={{ borderColor: color + "55" }}>
                    <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
                    {TYPE_LABEL[venue.type]}
                  </span>
                  {venue.region && (
                    <span className="chip">{REGION_LABEL[venue.region] || venue.region}</span>
                  )}
                </div>
                <h3 className="font-display text-lg leading-snug">
                  {onShowDetail ? (
                    <button type="button" onClick={() => onShowDetail(venueId)} className="text-left hover:underline">
                      {venue.name}
                    </button>
                  ) : venue.website ? (
                    <a href={venue.website} target="_blank" rel="noreferrer" className="hover:underline">{venue.name}</a>
                  ) : venue.name}
                  {venue.neighborhood && (
                    <span className="ml-1 text-sm font-normal text-ink/50">· {venue.neighborhood}</span>
                  )}
                </h3>
              </div>

              {/* Exhibition list */}
              <ul className="divide-y divide-black/5">
                {shows.map((ev) => {
                  const closeIn = daysUntilClose(ev);
                  const closingSoon = closeIn !== null && closeIn >= 0 && closeIn <= 14;
                  return (
                    <li key={ev.id} className="flex items-start gap-2 py-2 first:pt-0 last:pb-0">
                      {onToggleFav && (
                        <StarButton
                          isFav={favs?.has(ev.id) ?? false}
                          onToggle={() => onToggleFav(ev.id)}
                          label={(favs?.has(ev.id) ? "Remove" : "Save") + " exhibition"}
                        />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium leading-snug">
                          {ev.url ? (
                            <a href={ev.url} target="_blank" rel="noreferrer" className="hover:underline">{ev.title}</a>
                          ) : ev.title}
                        </div>
                        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink/55">
                          {fmtRange(ev) && <span>{fmtRange(ev)}</span>}
                          {closingSoon && (
                            <span className="inline-flex items-center rounded-full bg-red-500 px-1.5 py-0.5 font-semibold text-white">
                              {closeIn === 0 ? "Closes today" : closeIn === 1 ? "Closes tomorrow" : `Closes in ${closeIn}d`}
                            </span>
                          )}
                        </div>
                        {ev.artists?.length > 0 && (
                          <div className="mt-0.5 text-xs text-ink/45">{ev.artists.join(", ")}</div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </article>
        );
      })}
    </div>
  );
}
