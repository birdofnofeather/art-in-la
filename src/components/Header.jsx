import React from "react";
import { MODES } from "../lib/constants.js";

export default function Header({ tab, setTab, mode, setMode, stats }) {
  const tabs = [
    { key: "map", label: "Map" },
    { key: "events", label: "Events" },
    { key: "venues", label: "Venues" },
    { key: "archive", label: "Archive" },
  ];

  // Helpful copy that swaps with mode.
  const subtitleEvents =
    "Upcoming events at museums, galleries, and community art spaces across Los Angeles County";
  const subtitleExhibitions =
    "Current and upcoming exhibitions at museums, galleries, and community art spaces across Los Angeles County";

  return (
    <header className="border-b border-black/10 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 md:px-6">
        <div className="flex-1">
          <h1 className="font-display text-2xl font-extrabold leading-none tracking-tight">
            <span>Art in LA</span>
            <span className="mx-3 text-ink/30">|</span>
            <span className="inline-flex items-center gap-1 align-middle">
              {MODES.map((m, i) => {
                const active = (mode || "events") === m.key;
                return (
                  <React.Fragment key={m.key}>
                    {i > 0 && (
                      <span aria-hidden className="px-1 text-ink/30 font-medium">/</span>
                    )}
                    <button
                      type="button"
                      onClick={() => setMode && setMode(m.key)}
                      aria-pressed={active}
                      className={
                        active
                          ? "rounded-md bg-ink px-2 py-1 text-white shadow-sm"
                          : "rounded-md px-2 py-1 text-ink/50 hover:text-ink hover:bg-black/5"
                      }
                    >
                      {m.label}
                    </button>
                  </React.Fragment>
                );
              })}
            </span>
          </h1>
          <p className="mt-1 text-xs text-ink/60">
            {(mode || "events") === "exhibitions" ? subtitleExhibitions : subtitleEvents}
            {stats && (
              <>
                {" "}· {stats.venues} venues ·{" "}
                {(mode || "events") === "exhibitions"
                  ? `${stats.exhibitions} exhibitions`
                  : `${stats.events} upcoming events`}
              </>
            )}
          </p>
        </div>
        <nav className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                tab === t.key
                  ? "bg-ink text-white"
                  : "text-ink/70 hover:bg-black/5"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
