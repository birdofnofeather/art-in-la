import React from "react";
import { DISCIPLINES } from "../lib/constants.js";

// Archive is reachable via #tab=archive. Exhibitions are hidden while the
// Performing-arts view is selected (performing venues have none).
const TABS = [
  { key: "events",      label: "Events", primary: true },
  { key: "exhibitions", label: "Exhibitions", primary: true, visualOnly: true },
  { key: "map",         label: "Map" },
  { key: "venues",      label: "Venues" },
  { key: "saved",       label: "Saved" },
];

export function DisciplineSwitch({ discipline, setDiscipline }) {
  return (
    <div role="radiogroup" aria-label="Show venues"
      className="inline-flex rounded-full border border-ink/15 bg-white p-0.5 text-sm shadow-sm">
      {DISCIPLINES.map((d) => {
        const on = discipline === d.key;
        return (
          <button
            key={d.key} type="button" role="radio" aria-checked={on}
            onClick={() => setDiscipline(d.key)}
            title={d.long}
            className={`rounded-full px-3 py-1.5 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 md:py-1 ${
              on ? "bg-ink text-white" : "text-ink/70 hover:bg-black/5"
            }`}
          >
            {d.label}
          </button>
        );
      })}
    </div>
  );
}

export default function Header({
  tab, setTab, stats, savedCount, onHome, onAbout, lastUpdated, discipline, setDiscipline,
}) {
  const subtitle = discipline === "performing"
    ? "Performances at nonprofit performing-arts venues across LA County."
    : discipline === "all"
      ? "Exhibitions, events and performances at nonprofit arts venues across LA County."
      : "Exhibitions and events at nonprofit art venues across LA County.";
  const tabs = TABS.filter((t) => !(t.visualOnly && discipline === "performing"));
  return (
    <header className="border-b border-ink/10 bg-card md:sticky md:top-0 md:z-50">
      <div className="mx-auto max-w-7xl px-3 pt-3 md:px-6 md:pt-4">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
          <div className="min-w-0">
            <h1 className="site-title leading-none">
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); onHome?.(); }}
                className="rounded transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40"
              >
                Art in <span className="site-title-la">LA</span>
              </a>
            </h1>
            <p className="mt-1 text-xs text-ink/70">
              {subtitle}
              {stats && (
                <span className="hidden text-ink/55 sm:inline">
                  {" "}· {stats.venues} venues{stats.exhibitions != null ? ` · ${stats.exhibitions} exhibitions` : ""} · {stats.events} events
                </span>
              )}
              {lastUpdated && (
                <span className="hidden text-ink/45 md:inline">
                  {" "}· updated {lastUpdated.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </span>
              )}
            </p>
          </div>
          <DisciplineSwitch discipline={discipline} setDiscipline={setDiscipline} />
        </div>
        <nav aria-label="Primary"
          className="no-scrollbar -mx-3 mt-2 flex items-center gap-1 overflow-x-auto px-3 pb-2 md:mx-0 md:px-0">
          {tabs.map((t) => {
            const active = tab === t.key;
            return (
              <button
                key={t.key} type="button" onClick={() => setTab(t.key)}
                aria-current={active ? "page" : undefined}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 md:py-1.5 ${
                  t.primary ? "font-display font-bold" : "font-medium"
                } ${active ? "bg-ink text-white" : "text-ink/70 hover:bg-black/5"}`}
              >
                {t.label}
                {t.key === "saved" && savedCount > 0 && (
                  <span className={`inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full px-1 text-xs tabular-nums ${
                    active ? "bg-white/25 text-white" : "bg-accent text-white"
                  }`}>{savedCount}</span>
                )}
              </button>
            );
          })}
          {onAbout && (
            <button type="button" onClick={onAbout}
              className="ml-auto inline-flex shrink-0 items-center rounded-md px-3 py-2 text-sm font-medium text-ink/60 transition-colors hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 md:py-1.5">
              About
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
