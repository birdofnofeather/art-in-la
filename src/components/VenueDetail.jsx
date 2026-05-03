import React, { useEffect } from "react";
import { TYPE_COLOR, TYPE_LABEL, REGION_LABEL, EVENT_TYPE_LABEL } from "../lib/constants.js";
import { parseDate } from "../lib/filters.js";

function stripHtml(text) {
  if (!text) return "";
  return text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

const SOCIAL_ORDER = ["instagram", "twitter", "bluesky", "threads", "facebook", "tiktok", "youtube"];
const SOCIAL_LABEL = {
  instagram: "Instagram", twitter: "X / Twitter", bluesky: "Bluesky",
  threads: "Threads", facebook: "Facebook", tiktok: "TikTok", youtube: "YouTube",
};

const DATE_OPTS = { weekday: "short", month: "short", day: "numeric" };
const TIME_OPTS = { hour: "numeric", minute: "2-digit" };

function fmtDate(s) {
  if (!s) return null;
  const d = parseDate(s);
  if (!d) return s;
  const datePart = d.toLocaleDateString("en-US", DATE_OPTS);
  const hasT = typeof s === "string" && s.includes("T");
  return hasT ? `${datePart} · ${d.toLocaleTimeString("en-US", TIME_OPTS)}` : datePart;
}

function fmtRange(start, end) {
  const s = fmtDate(start);
  const e = fmtDate(end);
  if (!s) return null;
  if (!e || e === s) return s;
  return `${s} → ${e}`;
}

export default function VenueDetail({ venueId, venuesById, upcomingEvents, liveExhibitions, onClose, onShowOnMap }) {
  const v = venuesById?.[venueId];

  // Close on Escape
  useEffect(() => {
    if (!venueId) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [venueId, onClose]);

  if (!venueId || !v) return null;

  const color = TYPE_COLOR[v.type] || "#666";
  const socials = v.socials || {};
  const vEvents = (upcomingEvents || []).filter((e) => e.venue_id === venueId);
  const vExhibitions = (liveExhibitions || []).filter((e) => e.venue_id === venueId);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer */}
      <aside className="fixed right-0 top-0 bottom-0 z-50 flex w-full max-w-md flex-col bg-white shadow-2xl overflow-hidden">
        {/* Color bar */}
        <div className="h-1.5 w-full shrink-0" style={{ background: color }} />

        {/* Header */}
        <div className="flex items-start gap-3 px-6 py-5 border-b border-black/10">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-black/10 px-2.5 py-0.5 text-xs font-medium"
                style={{ borderColor: color + "55" }}>
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
                {TYPE_LABEL[v.type]}
              </span>
              {v.region && (
                <span className="text-xs text-ink/50">{REGION_LABEL[v.region] || v.region}</span>
              )}
            </div>
            <h2 className="font-display text-xl font-bold leading-tight">{v.name}</h2>
            {v.neighborhood && <div className="text-sm text-ink/60 mt-0.5">{v.neighborhood}</div>}
          </div>
          <button
            type="button" onClick={onClose}
            className="shrink-0 rounded-full p-1.5 hover:bg-black/5 text-ink/50 hover:text-ink transition-colors"
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

          {/* About */}
          {(v.description || v.address) && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink/40 mb-2">About</h3>
              {v.description && <p className="text-sm text-ink/70 leading-relaxed">{stripHtml(v.description)}</p>}
              {v.address && <p className="text-sm text-ink/50 mt-1">{v.address}</p>}
            </section>
          )}

          {/* Links */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink/40 mb-2">Links</h3>
            <div className="flex flex-wrap gap-2">
              {v.website && (
                <a href={v.website} target="_blank" rel="noreferrer"
                  className="chip">Website</a>
              )}
              {v.events_url && (
                <a href={v.events_url} target="_blank" rel="noreferrer"
                  className="chip">Events page</a>
              )}
              {v.address && (
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(v.address)}`}
                  target="_blank" rel="noreferrer" className="chip"
                >Directions</a>
              )}
              {onShowOnMap && typeof v.lat === "number" && (
                <button type="button" onClick={() => { onShowOnMap(venueId); onClose(); }} className="chip">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                  </svg>
                  Show on map
                </button>
              )}
              {SOCIAL_ORDER.filter((k) => socials[k]).map((k) => (
                <a key={k} href={socials[k]} target="_blank" rel="noreferrer" className="chip">
                  {SOCIAL_LABEL[k]}
                </a>
              ))}
            </div>
          </section>

          {/* Upcoming events */}
          {vEvents.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink/40 mb-2">
                Upcoming events ({vEvents.length})
              </h3>
              <div className="space-y-2">
                {vEvents.map((ev) => (
                  <div key={ev.id} className="rounded-lg border border-black/8 p-3">
                    <div className="text-sm font-medium leading-snug">
                      {ev.url ? (
                        <a href={ev.url} target="_blank" rel="noreferrer" className="hover:underline">
                          {ev.title}
                        </a>
                      ) : ev.title}
                    </div>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-ink/50">
                      {ev.event_type && <span>{EVENT_TYPE_LABEL[ev.event_type] || ev.event_type}</span>}
                      {ev.start && <span>{fmtDate(ev.start)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Exhibitions */}
          {vExhibitions.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink/40 mb-2">
                Exhibitions ({vExhibitions.length})
              </h3>
              <div className="space-y-2">
                {vExhibitions.map((ex) => (
                  <div key={ex.id} className="rounded-lg border border-black/8 p-3">
                    <div className="text-sm font-medium leading-snug">
                      {ex.url ? (
                        <a href={ex.url} target="_blank" rel="noreferrer" className="hover:underline">
                          {ex.title}
                        </a>
                      ) : ex.title}
                    </div>
                    {(ex.start || ex.end) && (
                      <div className="text-xs text-ink/50 mt-0.5">
                        {fmtRange(ex.start, ex.end)}
                      </div>
                    )}
                    {ex.artists?.length > 0 && (
                      <div className="text-xs text-ink/50 mt-0.5">{ex.artists.join(", ")}</div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {vEvents.length === 0 && vExhibitions.length === 0 && (
            <p className="text-sm text-in