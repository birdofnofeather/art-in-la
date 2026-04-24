import React from "react";

export default function Header({ tab, setTab, stats }) {
  const tabs = [
    { key: "map", label: "Map" },
    { key: "events", label: "Events" },
    { key: "venues", label: "Venues" },
    { key: "archive", label: "Archive" },
  ];
  return (
    <header className="border-b border-black/10 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 md:px-6">
        <div className="flex-1">
          <h1 className="font-display text-2xl font-extrabold leading-none tracking-tight">
            Art in LA
          </h1>
          <p className="mt-1 text-xs text-ink/60">
            Museums, galleries, and community art spaces across Los Angeles County
            {stats && <> · {stats.venues} venues · {stats.events} upcoming events</>}
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
