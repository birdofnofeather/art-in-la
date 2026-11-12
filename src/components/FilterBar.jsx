import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  TYPE_LABEL, TYPE_DEF, REGION_LABEL, EVENT_TYPE_FILTERS, DATE_PRESETS,
} from "../lib/constants.js";

// One compact, mobile-first filter bar shared by every tab.
//
//   ┌ search ──────────────────────────────────────────────┐
//   [Today][This weekend][Next weekend][Next 7 days][Any date] | [Free][Family] [Filters •2]
//   (active-filter chips · Clear all)
//
// The chip row never wraps on phones — it scrolls sideways, so the controls
// take one line instead of four. Everything secondary (event type, area,
// venue type, a custom date range) lives behind "Filters": a bottom sheet on
// phones, an inline panel on larger screens.

function Chip({ on, onClick, children, className = "", title }) {
  return (
    <button
      type="button" onClick={onClick} aria-pressed={!!on} title={title}
      className={`chip shrink-0 whitespace-nowrap ${on ? "chip-active" : ""} ${className}`}
    >
      {children}
    </button>
  );
}

function Group({ label, children }) {
  return (
    <fieldset>
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/65">{label}</legend>
      <div className="flex flex-wrap gap-2">{children}</div>
    </fieldset>
  );
}

function toggleIn(set, key) {
  const next = new Set(set);
  next.has(key) ? next.delete(key) : next.add(key);
  return next;
}

function useIsSmall() {
  const [small, setSmall] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => setSmall(mq.matches);
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);
  return small;
}

export default function FilterBar({
  tab,
  query, setQuery,
  types, setTypes, typeOptions,
  eventTypes, setEventTypes,
  regions, setRegions,
  datePreset, setDatePreset,
  customStart, setCustomStart,
  customEnd, setCustomEnd,
  free, setFree,
  family, setFamily,
  onReset,
  resultLabel,
  groupByVenue = null, setGroupByVenue,
}) {
  const [open, setOpen] = useState(false);
  const small = useIsSmall();
  const sheetRef = useRef(null);

  const isArchive = tab === "archive";
  const showDates = tab === "events" || tab === "map";
  const showEventTypes = tab === "events";
  const showFreeFamily = tab === "events" || tab === "exhibitions" || tab === "map";
  const showMore = !isArchive && tab !== "saved";

  // Close the sheet with Escape, and lock page scroll while it is open on phones.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    if (small) document.body.style.overflow = "hidden";
    sheetRef.current?.focus();
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [open, small]);

  const opts = (typeOptions && typeOptions.length) ? typeOptions : Object.keys(TYPE_LABEL);
  const activeTypes = [...(types || [])].filter((t) => opts.includes(t));

  const pills = [];
  for (const t of activeTypes) pills.push({ label: TYPE_LABEL[t] || t, remove: () => setTypes(toggleIn(types, t)) });
  for (const r of regions || []) pills.push({ label: REGION_LABEL[r] || r, remove: () => setRegions(toggleIn(regions, r)) });
  if (showEventTypes) {
    for (const et of eventTypes || []) {
      const f = EVENT_TYPE_FILTERS.find((x) => x.key === et);
      pills.push({ label: f?.label || et, remove: () => setEventTypes(toggleIn(eventTypes, et)) });
    }
  }
  if (showDates && datePreset === "custom" && (customStart || customEnd)) {
    pills.push({
      label: `${customStart || "…"} → ${customEnd || "…"}`,
      remove: () => { setCustomStart(""); setCustomEnd(""); setDatePreset("next7"); },
    });
  }
  const moreCount = pills.length;

  const panel = (
    <div className="space-y-5">
      {showEventTypes && (
        <Group label="What">
          {EVENT_TYPE_FILTERS.map((f) => (
            <Chip key={f.key} on={eventTypes.has(f.key)} onClick={() => setEventTypes(toggleIn(eventTypes, f.key))}>
              {f.label}
            </Chip>
          ))}
        </Group>
      )}
      <Group label="Area">
        {Object.keys(REGION_LABEL).map((r) => (
          <Chip key={r} on={regions.has(r)} onClick={() => setRegions(toggleIn(regions, r))}>{REGION_LABEL[r]}</Chip>
        ))}
      </Group>
      <Group label="Venue type">
        {opts.map((t) => (
          <Chip key={t} on={types.has(t)} title={TYPE_DEF[t]} onClick={() => setTypes(toggleIn(types, t))}>
            {TYPE_LABEL[t] || t}
          </Chip>
        ))}
      </Group>
      {showDates && (
        <fieldset>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/65">Specific dates</legend>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <label className="flex items-center gap-1.5">
              <span className="text-ink/65">From</span>
              <input type="date" value={customStart || ""} className="rounded-md border border-black/15 bg-white px-2 py-1"
                onChange={(e) => { setCustomStart(e.target.value); setDatePreset("custom"); }} />
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-ink/65">To</span>
              <input type="date" value={customEnd || ""} className="rounded-md border border-black/15 bg-white px-2 py-1"
                onChange={(e) => { setCustomEnd(e.target.value); setDatePreset("custom"); }} />
            </label>
          </div>
        </fieldset>
      )}
    </div>
  );

  return (
    <div className="panel sticky top-0 z-40 md:static">
      <div className="flex items-center gap-2 px-3 pt-3 md:px-4">
        <div className="relative min-w-0 flex-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink/65">
            <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="search" value={query || ""} onChange={(e) => setQuery(e.target.value)}
            placeholder={tab === "venues" ? "Search venues…" : "Search titles, venues, artists…"}
            aria-label="Search"
            className="w-full rounded-md border border-black/15 bg-white py-2 pl-8 pr-8 text-base placeholder:text-ink/65 focus:border-ink/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 md:py-1.5 md:text-sm"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} aria-label="Clear search"
              className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-lg text-ink/65 hover:text-ink">×</button>
          )}
        </div>
          {showMore && (
            <button
              type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
              className={`chip shrink-0 whitespace-nowrap py-2 md:py-1 ${moreCount ? "border-ink" : ""}`}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M3 6h18M7 12h10M10 18h4" />
              </svg>
              Filters
              {moreCount > 0 && (
                <span className="rounded-full bg-ink px-1.5 text-xs font-medium text-white">{moreCount}</span>
              )}
            </button>
          )}
      </div>

      {!isArchive && (
        <div className="no-scrollbar flex items-center gap-2 overflow-x-auto px-3 py-2.5 md:flex-wrap md:overflow-visible md:px-4">
          {showDates && DATE_PRESETS.map((p) => (
            <Chip key={p.key} on={(datePreset || "all") === p.key} onClick={() => setDatePreset(p.key)}>{p.label}</Chip>
          ))}
          {showDates && showFreeFamily && <span aria-hidden className="mx-0.5 h-5 w-px shrink-0 bg-ink/15" />}
          {showFreeFamily && (
            <>
              <Chip on={free} onClick={() => setFree(!free)} className="chip-free">Free</Chip>
              <Chip on={family} onClick={() => setFamily(!family)} className="chip-family" title="Tagged for families and kids">
                Family
              </Chip>
            </>
          )}
        </div>
      )}

      {(pills.length > 0 || resultLabel || groupByVenue !== null) && !isArchive && (
        <div className="flex flex-wrap items-center gap-2 border-t border-black/5 px-3 py-2 text-xs md:px-4">
          {resultLabel && <span role="status" aria-live="polite" className="text-ink/65">{resultLabel}</span>}
          {groupByVenue !== null && (
            <button type="button" onClick={() => setGroupByVenue(!groupByVenue)} aria-pressed={groupByVenue}
              title="Show each venue's events together in one card"
              className={`chip shrink-0 ${groupByVenue ? "chip-active" : ""}`}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <rect x="3" y="4" width="18" height="6" rx="1.5" /><rect x="3" y="14" width="18" height="6" rx="1.5" />
              </svg>
              Group by venue
            </button>
          )}
          {pills.map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 rounded-full bg-ink px-2.5 py-0.5 font-medium text-white">
              {p.label}
              <button type="button" onClick={p.remove} aria-label={`Remove ${p.label}`} className="-mr-1 px-1 hover:text-white/70">×</button>
            </span>
          ))}
          {(pills.length > 0 || free || family || query) && (
            <button type="button" onClick={onReset} className="text-ink/65 underline-offset-2 hover:text-ink hover:underline">
              Clear all
            </button>
          )}
        </div>
      )}

      {/* Secondary filters: inline panel (desktop) / bottom sheet (phone). */}
      {open && !small && (
        <div className="border-t border-black/5 px-4 py-4">
          {panel}
          <div className="mt-4 flex justify-end">
            <button type="button" className="chip" onClick={() => setOpen(false)}>Done</button>
          </div>
        </div>
      )}
      {open && small && createPortal(
        <div className="fixed inset-0 z-[1100] flex flex-col justify-end" role="dialog" aria-modal="true" aria-label="Filters">
          <button type="button" aria-label="Close filters" className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div ref={sheetRef} tabIndex={-1}
            className="relative max-h-[85vh] overflow-y-auto rounded-t-2xl bg-card px-4 pb-4 pt-3 shadow-2xl focus:outline-none">
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-ink/20" aria-hidden />
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">Filters</h2>
              <button type="button" className="text-sm text-ink/65 underline" onClick={onReset}>Reset</button>
            </div>
            {panel}
            <button type="button" onClick={() => setOpen(false)}
              className="sticky bottom-0 mt-5 w-full rounded-lg bg-ink py-3 text-sm font-semibold text-white">
              {resultLabel ? `Show ${resultLabel}` : "Done"}
            </button>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
