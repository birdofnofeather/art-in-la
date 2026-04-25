import React, { useState } from "react";
import {
  TYPE_LABEL, TYPE_COLOR, REGION_LABEL,
  EVENT_TYPE_FILTERS, DATE_PRESETS, EXHIBITION_STATUSES,
} from "../lib/constants.js";

function ToggleGroup({ label, options, labelMap, selected, onChange, colorMap }) {
  const toggle = (key) => {
    const next = new Set(selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onChange(next);
  };
  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">
        {label}
      </div>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => toggle(opt)}
            className={`chip ${selected.has(opt) ? "chip-active" : ""}`}
            style={
              colorMap && !selected.has(opt)
                ? { borderColor: colorMap[opt] + "55" }
                : undefined
            }
          >
            {colorMap && (
              <span
                aria-hidden
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: colorMap[opt] }}
              />
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
        <button
          key={it.key}
          type="button"
          onClick={() => onSelect(it.key)}
          className={`chip ${selectedKey === it.key ? "chip-active" : ""}`}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

function EventTypeChips({ selected, onChange }) {
  const toggle = (key) => {
    const next = new Set(selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onChange(next);
  };
  return (
    <div className="flex flex-wrap gap-2">
      {EVENT_TYPE_FILTERS.map((f) => (
        <button
          key={f.key}
          type="button"
          onClick={() => toggle(f.key)}
          className={`chip ${selected.has(f.key) ? "chip-active" : ""}`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

export default function FilterBar({
  tab,
  mode,
  types, setTypes,
  eventTypes, setEventTypes,
  regions, setRegions,
  datePreset, setDatePreset,
  exhibitionStatus, setExhibitionStatus,
  onReset,
}) {
  const [open, setOpen] = useState(false);

  const isExhibitions = mode === "exhibitions";

  // The Venues tab is venue-only (no event/date filters). The Events tab in
  // exhibitions mode swaps the event-type / date filters for a status picker.
  const showEventFilters = tab !== "venues" && !isExhibitions;
  const showExhibitionStatus = tab !== "venues" && isExhibitions;

  // Quick summary of active filter counts for the closed-tray button.
  const activeCount =
    (types?.size || 0) +
    (regions?.size || 0) +
    (showEventFilters ? (eventTypes?.size || 0) : 0) +
    (showEventFilters && datePreset && datePreset !== "all" ? 1 : 0) +
    (showExhibitionStatus && exhibitionStatus && exhibitionStatus !== "current" ? 1 : 0);

  return (
    <div className="panel">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="font-display text-sm font-semibold tracking-tight">
            Filter results
          </span>
          {activeCount > 0 && (
            <span className="rounded-full bg-ink px-2 py-0.5 text-xs font-medium text-white">
              {activeCount}
            </span>
          )}
        </div>
        <span className="text-xs text-ink/60">
          {open ? "Hide ▲" : "Show ▼"}
        </span>
      </button>

      {open && (
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
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">
                  Event type
                </div>
                <EventTypeChips selected={eventTypes} onChange={setEventTypes} />
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">
                  Dates
                </div>
                <FilterChips
                  items={DATE_PRESETS}
                  selectedKey={datePreset || "all"}
                  onSelect={setDatePreset}
                />
              </div>
            </>
          )}

          {showExhibitionStatus && (
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">
                Show
              </div>
              <FilterChips
                items={EXHIBITION_STATUSES}
                selectedKey={exhibitionStatus || "current"}
                onSelect={setExhibitionStatus}
              />
            </div>
          )}

          <div className="flex items-center justify-end pt-1">
            <button type="button" onClick={onReset} className="chip">
              Reset filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
