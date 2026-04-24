import React from "react";
import {
  TYPE_LABEL, TYPE_COLOR, REGION_LABEL, EVENT_TYPE_LABEL,
} from "../lib/constants.js";

function Toggle({ on, onChange, children }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!on)}
      className={`chip ${on ? "chip-active" : ""}`}
    >
      {children}
    </button>
  );
}

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

export default function FilterBar({
  types, setTypes,
  eventTypes, setEventTypes,
  regions, setRegions,
  startDate, setStartDate,
  endDate, setEndDate,
  eventfulOnly, setEventfulOnly,
  onReset,
}) {
  return (
    <div className="panel p-4 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Toggle on={eventfulOnly} onChange={setEventfulOnly}>
          <span className="inline-block h-2 w-2 rounded-full bg-amber-500" />
          Only venues with upcoming events
        </Toggle>
        <button type="button" onClick={onReset} className="chip">
          Reset filters
        </button>
      </div>

      <ToggleGroup
        label="Organization type"
        options={Object.keys(TYPE_LABEL)}
        labelMap={TYPE_LABEL}
        selected={types}
        onChange={setTypes}
        colorMap={TYPE_COLOR}
      />

      <ToggleGroup
        label="Event type"
        options={Object.keys(EVENT_TYPE_LABEL)}
        labelMap={EVENT_TYPE_LABEL}
        selected={eventTypes}
        onChange={setEventTypes}
      />

      <ToggleGroup
        label="Region"
        options={Object.keys(REGION_LABEL)}
        labelMap={REGION_LABEL}
        selected={regions}
        onChange={setRegions}
      />

      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink/50">
          Dates
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-ink/60">From</span>
            <input
              type="date"
              value={startDate || ""}
              onChange={(e) => setStartDate(e.target.value || null)}
              className="rounded-md border border-black/10 bg-white px-2 py-1 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-ink/60">To</span>
            <input
              type="date"
              value={endDate || ""}
              onChange={(e) => setEndDate(e.target.value || null)}
              className="rounded-md border border-black/10 bg-white px-2 py-1 text-sm"
            />
          </label>
        </div>
      </div>
    </div>
  );
}
