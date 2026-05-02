import React from "react";

const TABS = [
  { key: "map",     label: "Map" },
  { key: "events",  label: "Events" },
  { key: "venues",  label: "Venues" },
  { key: "archive", label: "Archive" },
];

export default function Header({ tab, setTab, stats }) {
  return (
    <header className="border-b border-black/10 bg-white sticky top-0 z-50">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 md:px-6">
        <div className="flex-1 min-w-0">
          <h1 className="font-display text-2xl font-extrabold leading-none tracking-tight">
            Art in LA
          </h1>
          <p className="mt-1 text-xs text-ink/60 truncate">
            Art events and exhibitions across Los Angeles County
            {stats && (
              <> · {stats.venues} venues · {stats.events} upcoming events · {stats.exhibitions} exhibitions</>
            )}
          </p>
        </div>
        <nav className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.key} type="button" onClick={() => setTab(t.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.key ? "bg-ink text-white" : "text-ink/70 hover:bg-black/5"
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
