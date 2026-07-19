import React from "react";

// Archive is intentionally NOT here — it's reachable via #tab=archive.
// Map is hidden on small screens (Leaflet + touch is not reliable enough).
const TABS = [
  { key: "whatson",      label: "What's On", primary: true },
  { key: "events",       label: "Events" },
  { key: "exhibitions",  label: "Exhibitions" },
  { key: "venues",       label: "Venues" },
  { key: "map",          label: "Map", desktopOnly: true },
  { key: "saved",        label: "Saved" },
];

export default function Header({ tab, setTab, stats, savedCount, onHome, onAbout }) {
  return (
    <header className="border-b border-ink/10 bg-card sticky top-0 z-50">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-1 px-4 pb-2 pt-3 md:py-4">
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-xl font-extrabold leading-none tracking-tight md:text-2xl">
            {onHome ? (
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); onHome(); }}
                className="hover:opacity-70 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 rounded"
              >
                Art in LA
              </a>
            ) : "Art in LA"}
          </h1>
          <p className="mt-1 hidden text-xs text-ink/70 md:block">
            The visual-art calendar for LA County
            {stats && (
              <> · {stats.venues} venues · {stats.events} events · {stats.exhibitions} exhibitions</>
            )}
          </p>
        </div>
        <nav
          aria-label="Primary"
          className="-mx-4 flex w-[calc(100%+2rem)] items-center gap-1 overflow-x-auto px-4 pb-1 md:mx-0 md:w-auto md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
        >
          {TABS.map((t) => {
            const active = tab === t.key;
            return (
              <button
                key={t.key} type="button" onClick={() => setTab(t.key)}
                aria-current={active ? "page" : undefined}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 md:py-1.5 ${
                  t.desktopOnly ? "hidden md:inline-flex" : ""
                } ${
                  t.primary ? "font-display text-[15px] font-bold" : "font-medium"
                } ${
                  active ? "bg-ink text-white" : "text-ink/70 hover:bg-black/5"
                }`}
              >
                {t.label}
                {t.key === "saved" && savedCount > 0 && (
                  <span className={`inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full px-1 text-xs tabular-nums ${
                    active ? "bg-white/25 text-white" : "bg-accent text-white"
                  }`}>
                    {savedCount}
                  </span>
                )}
              </button>
            );
          })}
          {onAbout && (
            <button
              type="button"
              onClick={onAbout}
              className="inline-flex shrink-0 items-center rounded-md px-3 py-2 text-sm font-medium text-ink/70 transition-colors hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40 md:py-1.5"
            >
              About
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
