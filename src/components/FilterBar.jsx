import React, { useState } from "react";
import {
  TYPE_LABEL, TYPE_COLOR, TYPE_DEF, REGION_LABEL,
  EVENT_TYPE_FILTERS, DATE_PRESETS, PRIMARY_DATE_PRESETS,
} from "../lib/constants.js";

function ToggleGroup({ label, options, labelMap, selected, onChange, colorMap, tipMap }) {
  const toggle = (key) => {
    const next = new Set(selected);
    next.has(key) ? next.delete(key) : next.add(key);
    onChange(next);
  };
  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/60">{label}</div>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const on = selected.has(opt);
          return (
            <button
              key={opt} type="button" onClick={() => toggle(opt)}
              title={tipMap?.[opt]}
              aria-pressed={on}
              aria-label={tipMap?.[opt] ? `${(labelMap && labelMap[opt]) || opt} — ${tipMap[opt]}` : undefined}
              className={`chip ${on ? "chip-active" : ""}`}
              style={colorMap && !on ? { borderColor: colorMap[opt] + "55" } : undefined}
            >
              {colorMap && (
                <span aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: colorMap[opt] }} />
              )}
              {(labelMap && labelMap[opt]) || opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function FilterChips({ items, selectedKey, onSelect }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => (
        <button key={it.key} type="button" onClick={() => onSelect(it.key)}
          aria-pressed={selectedKey === it.key}
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
      {EVENT_TYPE_FILTERS.map((f) => {
        const on = selected.has(f.key);
        return (
          <button key={f.key} type="button" onClick={() => toggle(f.key)}
            aria-pressed={on}
            className={`chip ${on ? "chip-active" : ""}`}>
            {f.label}
          </button>
        );
      })}
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

const PRIMARY_PRESET_ITEMS = DATE_PRESETS.filter((p) => PRIMARY_DATE_PRESETS.includes(p.key));
const SECONDARY_PRESET_ITEMS = DATE_PRESETS.filter((p) => !PRIMARY_DATE_PRESETS.includes(p.key));

export default function FilterBar({
  tab,
  query, setQuery,
  types, setTypes,
  eventTypes, setEventTypes,
  regions, setRegions,
  datePreset, setDatePreset,
  customStart, setCustomStart,
  customEnd, setCustomEnd,
  free, setFree,
  family, setFamily,
  onReset,
}) {
  const [open, setOpen] = useState(false);

  const isArchive = tab === "archive";
  const showEventFilters = tab === "events" || tab === "whatson";
  const showDates = tab === "events" || tab === "whatson";
  const showFreeFamily = tab === "events" || tab === "whatson" || tab === "exhibitions";
  const showPrimaryRow = !isArchive && (showDates || showFreeFamily);

  const activeCount =
    (types?.size   || 0) +
    (regions?.size  || 0) +
    (showEventFilters ? (eventTypes?.size || 0) : 0) +
    (showDates && datePreset && datePreset !== "all" ? 1 : 0) +
    (showFreeFamily && free ? 1 : 0) +
    (showFreeFamily && family ? 1 : 0);

  // Pills for closed-tray summary (venue type + region + event type only; the
  // date/Free/Family controls live in the always-visible primary row).
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

  return (
    <div className="panel">
      {/* Search + filter toggle row */}
      <div className="flex w-full items-center gap-3 px-4 py-3">
        <div className="relative flex-1 min-w-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink/50">
            <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="text"
            value={query || ""}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search events, exhibitions, venues, artists…"
            aria-label="Search"
            className="w-full rounded-md border border-black/15 bg-white py-1.5 pl-8 pr-8 text-sm placeholder:text-ink/50 focus:border-ink/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-ink/50 hover:text-ink">×</button>
          )}
        </div>
        {!isArchive && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="flex shrink-0 items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 rounded"
          >
            <span className="text-xs text-ink/60" aria-hidden>{open ? "▲" : "▼"}</span>
            <span className="font-display text-sm font-semibold tracking-tight">Filters</span>
            {activeCount > 0 && (
              <span className="rounded-full bg-ink px-2 py-0.5 text-xs font-medium text-white">
                {activeCount}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Always-visible primary filters: dates + Free + Family */}
      {showPrimaryRow && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-black/5 px-4 py-2.5">
          {showDates && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">When</span>
              {PRIMARY_PRESET_ITEMS.map((it) => (
                <button key={it.key} type="button" onClick={() => setDatePreset(it.key)}
                  aria-pressed={(datePreset || "all") === it.key}
                  className={`chip ${(datePreset || "all") === it.key ? "chip-active" : ""}`}>
                  {it.label}
                </button>
              ))}
            </div>
          )}
          {showFreeFamily && (
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={() => setFree(!free)}
                aria-pressed={!!free}
                className={`chip ${free ? "chip-active" : ""}`}>
                Free
              </button>
              <button type="button" onClick={() => setFamily(!family)}
                aria-pressed={!!family}
                title="Events tagged for families / kids"
                className={`chip ${family ? "chip-active" : ""}`}>
                Family-friendly
              </button>
            </div>
          )}
        </div>
      )}

      {/* Active filter pills — shown when tray is closed */}
      {!isArchive && !open && activePills.length > 0 && (
        <div className="flex flex-wrap gap-2 border-t border-black/5 px-4 py-2">
          {activePills.map((p, i) => (
            <ActivePill key={i} label={p.label} onRemove={p.remove} />
          ))}
          <button type="button" onClick={onReset} className="text-xs text-ink/60 hover:text-ink underline-offset-2 hover:underline">
            Clear all
          </button>
        </div>
      )}

      {!isArchive && open && (
        <div className="space-y-4 border-t border-black/5 px-4 py-4">
          <ToggleGroup
            label="Venue type"
            options={Object.keys(TYPE_LABEL)}
            labelMap={TYPE_LABEL}
            selected={types}
            onChange={setTypes}
            colorMap={TYPE_COLOR}
            tipMap={TYPE_DEF}
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
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/60">Event type</div>
                <EventTypeChips selected={eventTypes} onChange={setEventTypes} />
              </div>
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/60">More dates</div>
                <FilterChips
                  items={SECONDARY_PRESET_ITEMS}
                  selectedKey={datePreset || "all"}
                  onSelect={setDatePreset}
                />
                {datePreset === "custom" && (
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-ink/60">From</label>
                      <input
                        type="date"
                        value={customStart || ""}
                        onChange={(e) => setCustomStart(e.target.value)}
                        className="rounded border border-black/20 px-2 py-1 text-sm"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-ink/60">To</label>
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
            <p className="text-xs text-ink/60">
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
