import React, { useState } from "react";
import {
  TYPE_LABEL, TYPE_COLOR, REGION_LABEL,
  EVENT_TYPE_FILTERS, DATE_PRESETS,
} from "../lib/constants.js";

function ToggleGroup({ label, options, labelMap, selected, onChange, colorMap }) {
  const toggle = (key) => {
    const next = new Set(selected);
    next.has(key) ? next.delete(key) : next.add(key);
    onChange(next);
  };
  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">{label}</div>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt} type="button" onClick={() => toggle(opt)}
            className={`chip ${selected.has(opt) ? "chip-active" : ""}`}
            style={colorMap && !selected.has(opt) ? { borderColor: colorMap[opt] + "55" } : undefined}
          >
            {colorMap && (
              <span aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: colorMap[opt] }} />
            )}
            {(labelMap && labelMap[opt]) || opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function FilterChips({ items, selectedKey, onSelect }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => (
        <button key={it.key} type="button" onClick={() => onSelect(it.key)}
          className={`chip ${selectedKey === it.key ? "chip-active" : ""}`}>
          {it.label}
        </button>
      ))}
    </div>
  );
}

function EventTypeChips({ selected, onChange }) {
  const toggle = (key) => {
    const next = new Set(selected);
    next.has(key) ? next.delete(key) : next.add(key);
    onChange(next);
  };
  return (
    <div className="flex flex-wrap gap-2">
      {EVENT_TYPE_FILTERS.map((f) => (
        <button key={f.key} type="button" onClick={() => toggle(f.key)}
          className={`chip ${selected.has(f.key) ? "chip-active" : ""}`}>
          {f.label}
        </button>
      ))}
    </div>
  );
}

/** Pill shown when the filter tray is closed and a filter is active. */
function ActivePill({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-ink px-2.5 py-0.5 text-xs font-medium text-white">
      {label}
      <button type="button" onClick={onRemove} aria-label={`Remove ${label} filter`}
        className="ml-0.5 rounded-full hover:text-white/70">×</button>
    </span>
  );
}

export default function FilterBar({
  tab,
  query, setQuery,
  types, setTypes,
  eventTypes, setEventTypes,
  regions, setRegions,
  datePreset, setDatePreset,
  customStart, setCustomStart,
  customEnd, setCustomEnd,
  onReset,
}) {
  const [open, setOpen] = useState(false);

  // Archive is filter-isolated: only free-text search applies there, so we hide
  // the org/region/event-type controls entirely (they must not cross over).
  const isArchive = tab === "archive";
  const showEventFilters = tab === "events";

  const activeCount =
    (types?.size   || 0) +
    (regions?.size  || 0) +
    (showEventFilters ? (eventTypes?.size || 0) : 0) +
    (showEventFilters && datePreset && datePreset !== "all" ? 1 : 0);

  // Build pills for closed-tray summary
  const activePills = [];
  if (types?.size) {
    for (const t of types) activePills.push({
      label: TYPE_LABEL[t] || t,
      remove: () => { const s = new Set(types); s.delete(t); setTypes(s); },
    });
  }
  if (regions?.size) {
    for (const r of regions) activePills.push({
      label: REGION_LABEL[r] || r,
      remove: () => { const s = new Set(regions); s.delete(r); setRegions(s); },
    });
  }
  if (showEventFilters && eventTypes?.size) {
    for (const et of eventTypes) {
      const f = EVENT_TYPE_FILTERS.find((x) => x.key === et);
      activePills.push({
        label: f?.label || et,
        remove: () => { const s = new Set(eventTypes); s.delete(et); setEventTypes(s); },
      });
    }
  }
  if (showEventFilters && datePreset && datePreset !== "all") {
    const p = DATE_PRESETS.find((x) => x.key === datePreset);
    activePills.push({
      label: datePreset === "custom" && (customStart || customEnd)
        ? `${customStart || "…"} → ${customEnd || "…"}`
        : (p?.label || datePreset),
      remove: () => { setDatePreset("all"); setCustomStart?.(""); setCustomEnd?.(""); },
    });
  }
  const showSearch = tab !== "map";

  return (
    <div className="panel">
      {/* Search + filter toggle row */}
      <div className="flex w-full items-center gap-3 px-4 py-3">
        {showSearch && (
          <div className="relative flex-1 min-w-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink/40">
              <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
            </svg>
            <input
              type="text"
              value={query || ""}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search events, exhibitions, venues, artists…"
              aria-label="Search"
              className="w-full rounded-md border border-black/15 bg-white py-1.5 pl-8 pr-8 text-sm placeholder:text-ink/40 focus:border-ink/40 focus:outline-none"
            />
            {query && (
              <button type="button" onClick={() => setQuery("")} aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-ink/40 hover:text-ink">×</button>
            )}
          </div>
        )}
        {!isArchive && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className={`flex items-center justify-between gap-3 text-left ${showSearch ? "shrink-0" : "w-full"}`}
          >
            <div className="flex items-center gap-2">
              <span className="font-display text-sm font-semibold tracking-tight">Filters</span>
              {activeCount > 0 && (
                <span className="rounded-full bg-ink px-2 py-0.5 text-xs font-medium text-white">
                  {activeCount}
                </span>
              )}
            </div>
            <span className="text-xs text-ink/60">{open ? "▲" : "▼"}</span>
          </button>
        )}
      </div>

      {/* Active filter pills — shown when tray is closed */}
      {!isArchive && !open && activePills.length > 0 && (
        <div className="flex flex-wrap gap-2 border-t border-black/5 px-4 py-2">
          {activePills.map((p, i) => (
            <ActivePill key={i} label={p.label} onRemove={p.remove} />
          ))}
          <button type="button" onClick={onReset} className="text-xs text-ink/40 hover:text-ink underline-offset-2 hover:underline">
            Clear all
          </button>
        </div>
      )}

      {!isArchive && open && (
        <div className="space-y-4 border-t border-black/5 px-4 py-4">
          <ToggleGroup
            label="Organization type"
            options={Object.keys(TYPE_LABEL)}
            labelMap={TYPE_LABEL}
            selected={types}
            onChange={setTypes}
            colorMap={TYPE_COLOR}
          />
          <ToggleGroup
            label="Region"
            options={Object.keys(REGION_LABEL)}
            labelMap={REGION_LABEL}
            selected={regions}
            onChange={setRegions}
          />

          {showEventFilters && (
            <>
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">Event type</div>
                <EventTypeChips selected={eventTypes} onChange={setEventTypes} />
              </div>
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">Dates</div>
                <FilterChips
                  items={DATE_PRESETS}
                  selectedKey={datePreset || "all"}
                  onSelect={setDatePreset}
                />
                {datePreset === "custom" && (
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-ink/50">From</label>
                      <input
                        type="date"
                        value={customStart || ""}
                        onChange={(e) => setCustomStart(e.target.value)}
                        className="rounded border border-black/20 px-2 py-1 text-sm"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-ink/50">To</label>
                      <input
                        type="date"
                        value={customEnd || ""}
                        onChange={(e) => setCustomEnd(e.target.value)}
                        className="rounded border border-black/20 px-2 py-1 text-sm"
                        min={customStart || undefined}
                      />
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "exhibitions" && (
            <p className="text-xs text-ink/50">
              Showing temporary exhibitions on view now, ending soonest first.
            </p>
          )}

          <div className="flex items-center justify-end pt-1">
            <button type="button" onClick={onReset} className="chip">Reset filters</button>
          </div>
        </div>
      )}
    </div>
  );
}
