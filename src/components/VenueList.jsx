import React from "react";
import { TYPE_COLOR, TYPE_LABEL, REGION_LABEL } from "../lib/constants.js";

const SOCIAL_ORDER = ["instagram", "twitter", "bluesky", "threads", "facebook", "tiktok", "youtube"];
const SOCIAL_LABEL = {
  instagram: "Instagram", twitter: "X / Twitter", bluesky: "Bluesky",
  threads: "Threads", facebook: "Facebook", tiktok: "TikTok", youtube: "YouTube",
};

export default function VenueList({ venues, eventfulIds, scrapedIds, onShowOnMap, onShowDetail }) {
  if (venues.length === 0) {
    return (
      <div className="panel p-6 text-center text-sm text-ink/60">
        No venues match these filters.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {venues.map((v) => {
        const color = TYPE_COLOR[v.type] || "#666";
        const socials = v.socials || {};
        const hasScraped = !scrapedIds || scrapedIds.has(v.id);

        return (
          <article key={v.id} className="panel overflow-hidden">
            <div className="h-1 w-full" style={{ background: color }} />
            <div className="space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="chip" style={{ borderColor: color + "55" }}>
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
                  {TYPE_LABEL[v.type]}
                </span>
                <span className="chip">{REGION_LABEL[v.region] || v.region}</span>
                {eventfulIds.has(v.id) && (
                  <span className="chip" style={{ borderColor: "#f59e0b55" }}>
                    <span className="inline-block h-2 w-2 rounded-full bg-amber-500" />
                    Upcoming event
                  </span>
                )}
                {!hasScraped && (
                  <span className="chip text-ink/40" title="No automated scraper — events added manually or not yet tracked">
                    No scraper
                  </span>
                )}
              </div>

              <h3 className="font-display text-lg leading-snug">
                {onShowDetail ? (
                  <button
                    type="button"
                    onClick={() => onShowDetail(v.id)}
                    className="hover:underline text-left"
                  >
                    {v.name}
                  </button>
                ) : v.website ? (
                  <a href={v.website} target="_blank" rel="noreferrer" className="hover:underline">
                    {v.name}
                  </a>
                ) : v.name}
              </h3>

              <div className="text-sm text-ink/70">{v.description}</div>
              <div className="text-xs text-ink/60">
                {v.address}
                {v.address && v.neighborhood && " · "}
                {!v.address && v.neighborhood}
              </div>

              <div className="flex flex-wrap gap-2 pt-1 text-xs">
                {v.events_url && (
                  <a href={v.events_url} target="_blank" rel="noreferrer" className="chip">Events</a>
                )}
                {v.address && (
                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(v.address)}`}
                    target="_blank" rel="noreferrer" className="chip"
                  >
                    Directions
                  </a>
                )}
                {SOCIAL_ORDER.filter((k) => socials[k]).map((k) => (
                  <a key={k} href={socials[k]} target="_blank" rel="noreferrer" className="chip">
                    {SOCIAL_LABEL[k]}
                  </a>
                ))}
                {onShowOnMap && typeof v.lat === "number" && (
                  <button
                    type="button"
                    onClick={() => onShowOnMap(v.id)}
                    className="chip"
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                    Show on map
                  </button>
                )}
                {onShowDetail && (
                  <button type="button" onClick={() => onShowDetail(v.id)} className="chip">
                    Details
                  </button>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
