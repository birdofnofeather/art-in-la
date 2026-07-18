import React, {
  lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState,
} from "react";
import Header from "./components/Header.jsx";
import FilterBar from "./components/FilterBar.jsx";
import EventList from "./components/EventList.jsx";
import ExhibitionsByVenue from "./components/ExhibitionsByVenue.jsx";
import VenueList from "./components/VenueList.jsx";
import VenueDetail from "./components/VenueDetail.jsx";
import AboutDialog from "./components/AboutDialog.jsx";
import { loadAll } from "./lib/data.js";
import { useFavorites } from "./lib/useFavorites.js";
import {
  indexVenues, filterVenues, filterEvents, sortEvents,
  eventfulVenueIds, isUpcoming, partitionByMode, liveExhibitionsOnView,
  sortByEndingSoonest, searchEvents, searchVenues,
} from "./lib/filters.js";
import { ARCHIVE_LAUNCH_DATE } from "./lib/constants.js";

// Lazy-load the Leaflet map — keeps it out of the initial bundle (~150 kb).
const VenueMap = lazy(() => import("./components/VenueMap.jsx"));

// ── URL hash helpers ──────────────────────────────────────────────────────────
function readHash() {
  try { return new URLSearchParams(window.location.hash.slice(1)); }
  catch { return new URLSearchParams(); }
}
function writeHash(params) {
  const str = params.toString();
  window.history.replaceState(null, "", str ? "#" + str : window.location.pathname);
}

// ── Skeleton card ─────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="panel overflow-hidden animate-pulse">
      <div className="h-1 w-full bg-ink/10" />
      <div className="space-y-3 p-4">
        <div className="flex gap-2">
          <div className="h-5 w-16 rounded-full bg-ink/10" />
          <div className="h-5 w-20 rounded-full bg-ink/10" />
        </div>
        <div className="h-6 w-3/4 rounded bg-ink/10" />
        <div className="h-4 w-1/2 rounded bg-ink/10" />
        <div className="h-4 w-1/3 rounded bg-ink/10" />
      </div>
    </div>
  );
}
function SkeletonGrid({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {Array.from({ length: count }, (_, i) => <SkeletonCard key={i} />)}
    </div>
  );
}

// Each tab keeps its own filters so a filter set on one page never affects
// another. A stable shared "empty" keeps identities steady for untouched tabs
// (its Sets are never mutated — toggles always create a fresh Set).
const EMPTY_FILTERS = Object.freeze({
  types: new Set(), regions: new Set(), eventTypes: new Set(),
  datePreset: "all", customStart: "", customEnd: "", query: "",
});

// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [data, setData]         = useState({ venues: [], events: [], archive: [], scrapedVenues: [] });

  // Favorites (persisted to localStorage)
  const { favs, toggle: toggleFav } = useFavorites();

  // Navigation
  const [tab,  setTab]  = useState("map");

  // Per-tab filters (isolated — filtering one page never affects another).
  const [filtersByTab, setFiltersByTab] = useState({});
  const f = filtersByTab[tab] ?? EMPTY_FILTERS;
  const { types, regions, eventTypes, datePreset, customStart, customEnd, query } = f;
  const patchFilters = useCallback((p) => {
    setFiltersByTab((prev) => ({ ...prev, [tab]: { ...(prev[tab] ?? EMPTY_FILTERS), ...p } }));
  }, [tab]);
  const setTypes       = (v) => patchFilters({ types: v });
  const setRegions     = (v) => patchFilters({ regions: v });
  const setEventTypes  = (v) => patchFilters({ eventTypes: v });
  const setDatePreset  = (v) => patchFilters({ datePreset: v });
  const setCustomStart = (v) => patchFilters({ customStart: v });
  const setCustomEnd   = (v) => patchFilters({ customEnd: v });
  const setQuery       = (v) => patchFilters({ query: v });

  // Map filter toggle
  const [mapOnlyEventful, setMapOnlyEventful] = useState(true);

  // Cross-linking: which venue is "focused" on the map
  const [focusedVenueId, setFocusedVenueId] = useState(null);

  // Venue detail panel
  const [detailVenueId, setDetailVenueId] = useState(null);

  // Archive sub-view: past events vs past exhibitions
  const [archiveMode, setArchiveMode] = useState("events");

  // Events tab: collapse each venue's events into one stacked card (e.g. Academy
  // Museum's near-daily screenings).
  const [stackByVenue, setStackByVenue] = useState(false);

  // About / feedback dialog
  const [aboutOpen, setAboutOpen] = useState(false);

  // ── URL hash: read on mount ────────────────────────────────────────────────
  const hashInit = useRef(false);
  useEffect(() => {
    if (hashInit.current) return;
    hashInit.current = true;
    const p = readHash();
    const initTab = p.get("mode") === "exhibitions" ? "exhibitions" : (p.get("tab") || "map");
    // Hydrate only the initial tab's filter slice from the URL.
    const slice = { ...EMPTY_FILTERS };
    if (p.get("types"))   slice.types = new Set(p.get("types").split(","));
    if (p.get("regions")) slice.regions = new Set(p.get("regions").split(","));
    if (p.get("etypes"))  slice.eventTypes = new Set(p.get("etypes").split(","));
    if (p.get("date"))    slice.datePreset = p.get("date");
    if (p.get("from"))    slice.customStart = p.get("from");
    if (p.get("to"))      slice.customEnd = p.get("to");
    if (p.get("q"))       slice.query = p.get("q");
    setFiltersByTab({ [initTab]: slice });
    setTab(initTab);
    if (p.get("map"))   setMapOnlyEventful(p.get("map") !== "all");
    if (p.get("venue")) setDetailVenueId(p.get("venue"));
  }, []);

  // ── URL hash: write the ACTIVE tab's filters ──────────────────────────────
  useEffect(() => {
    if (!hashInit.current) return;
    const p = new URLSearchParams();
    p.set("tab", tab);
    if (types.size)   p.set("types",   [...types].join(","));
    if (regions.size) p.set("regions", [...regions].join(","));
    if (eventTypes.size) p.set("etypes", [...eventTypes].join(","));
    if (datePreset && datePreset !== "all") p.set("date", datePreset);
    if (customStart) p.set("from", customStart);
    if (customEnd)   p.set("to",   customEnd);
    if (!mapOnlyEventful) p.set("map", "all");
    if (query.trim()) p.set("q", query.trim());
    if (detailVenueId) p.set("venue", detailVenueId);
    writeHash(p);
  }, [tab, types, regions, eventTypes, datePreset, customStart, customEnd, mapOnlyEventful, query, detailVenueId]);

  // ── Data load (extracted for retry) ───────────────────────────────────────
  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    loadAll()
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, []);
  useEffect(() => { load(); }, [load]);

  // ── Derived data ──────────────────────────────────────────────────────────
  const venuesById  = useMemo(() => indexVenues(data.venues),   [data.venues]);
  const scrapedIds  = useMemo(() => new Set(data.scrapedVenues || []), [data.scrapedVenues]);

  const { oneoff: allOneoff, exhibitions: allExhibitions } = useMemo(
    () => partitionByMode(data.events), [data.events]
  );
  const upcomingEvents  = useMemo(() => allOneoff.filter((ev) => isUpcoming(ev)),      [allOneoff]);
  const liveExhibitions = useMemo(() => allExhibitions.filter((ev) => isUpcoming(ev)), [allExhibitions]);
  const eventfulIds     = useMemo(() => eventfulVenueIds(upcomingEvents),  [upcomingEvents]);

  // Map shows all or eventful-only depending on toggle
  const eventfulFilter = tab === "map" && mapOnlyEventful;

  const filteredVenues = useMemo(
    () => searchVenues(
      filterVenues(data.venues, { types, regions, eventful: eventfulFilter, eventfulIds }),
      query
    ),
    [data.venues, types, regions, eventfulFilter, eventfulIds, query]
  );

  const filteredEvents = useMemo(
    () => sortEvents(searchEvents(filterEvents(upcomingEvents, venuesById, {
      venueTypes: types, eventTypes, regions,
      datePreset: datePreset !== "custom" ? datePreset : "all",
      startDate: datePreset === "custom" ? customStart : undefined,
      endDate:   datePreset === "custom" ? customEnd   : undefined,
    }), venuesById, query)),
    [upcomingEvents, venuesById, types, eventTypes, regions, datePreset, customStart, customEnd, query]
  );

  const filteredExhibitions = useMemo(
    () => sortByEndingSoonest(searchEvents(filterEvents(
      liveExhibitionsOnView(liveExhibitions),
      venuesById, { venueTypes: types, regions }
    ), venuesById, query)),
    [liveExhibitions, venuesById, types, regions, query]
  );

  // Archive holds both past events and past exhibitions. It is deliberately
  // ISOLATED from the org/region/event-type filters used on other tabs (those
  // shouldn't carry over here) — only the Events/Exhibitions toggle and the
  // free-text search apply.
  const { oneoff: archiveOneoff, exhibitions: archiveExhibitions } = useMemo(
    () => partitionByMode(data.archive), [data.archive]
  );
  const filteredArchive = useMemo(() => {
    const base = archiveMode === "exhibitions" ? archiveExhibitions : archiveOneoff;
    return sortEvents(searchEvents(base, venuesById, query)).reverse();
  }, [archiveMode, archiveOneoff, archiveExhibitions, venuesById, query]);

  // Saved items
  const savedEvents = useMemo(
    () => [...upcomingEvents, ...liveExhibitions].filter((ev) => favs.has(ev.id)),
    [upcomingEvents, liveExhibitions, favs]
  );
  const savedVenues = useMemo(
    () => data.venues.filter((v) => favs.has(v.id)),
    [data.venues, favs]
  );

  // Freshness signal: newest scraped_at across all events.
  const lastUpdated = useMemo(() => {
    let max = null;
    for (const ev of data.events) {
      if (ev.scraped_at && (!max || ev.scraped_at > max)) max = ev.scraped_at;
    }
    return max ? new Date(max) : null;
  }, [data.events]);

  // Clear detailVenueId if the venue isn't in the loaded data (defensive).
  useEffect(() => {
    if (detailVenueId && Object.keys(venuesById).length > 0 && !venuesById[detailVenueId]) {
      setDetailVenueId(null);
    }
  }, [detailVenueId, venuesById]);

  // ── Callbacks ─────────────────────────────────────────────────────────────
  // Reset clears only the current tab's filters.
  const onReset = () => setFiltersByTab((prev) => ({ ...prev, [tab]: { ...EMPTY_FILTERS } }));

  const onHome = () => {
    setFiltersByTab({});            // clear every tab's filters
    setMapOnlyEventful(true);
    setFocusedVenueId(null);
    setDetailVenueId(null);
    setTab("map");
  };

  const onShowOnMap = (venueId) => {
    setFocusedVenueId(null);
    setTimeout(() => setFocusedVenueId(venueId), 0);
    setTab("map");
  };

  const onGoToEvents = (venueId) => {
    const venue = venuesById[venueId];
    // Target the Events tab's own slice (not the current tab's).
    setFiltersByTab((prev) => ({
      ...prev,
      events: { ...(prev.events ?? EMPTY_FILTERS), query: venue?.name || "" },
    }));
    setTab("events");
  };

  const stats = {
    venues:      data.venues.length,
    events:      upcomingEvents.length,
    exhibitions: liveExhibitions.length,
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      <Header tab={tab} setTab={setTab} stats={loading ? null : stats} savedCount={favs.size} onHome={onHome} />

      <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {/* Error panel with retry */}
        {error && (
          <div className="panel p-6 text-center space-y-3">
            <p className="text-sm font-medium">We couldn't load the latest event data.</p>
            <p className="text-xs text-ink/50">{error}</p>
            <button type="button" onClick={load} className="chip">
              Try again
            </button>
          </div>
        )}

        {/* FilterBar always visible (even while loading) */}
        <FilterBar
          tab={tab}
          query={query} setQuery={setQuery}
          types={types} setTypes={setTypes}
          eventTypes={eventTypes} setEventTypes={setEventTypes}
          regions={regions} setRegions={setRegions}
          datePreset={datePreset} setDatePreset={setDatePreset}
          customStart={customStart} setCustomStart={setCustomStart}
          customEnd={customEnd}     setCustomEnd={setCustomEnd}
          onReset={onReset}
        />

        {loading ? (
          <SkeletonGrid count={tab === "map" ? 0 : 6} />
        ) : (
          <>
            {tab === "map" && (
              <Suspense fallback={<div className="panel p-6 text-center text-sm text-ink/60">Loading map…</div>}>
                <VenueMap
                  venues={filteredVenues}
                  eventfulIds={eventfulIds}
                  onlyEventful={mapOnlyEventful}
                  setOnlyEventful={setMapOnlyEventful}
                  upcomingEvents={upcomingEvents}
                  focusedVenueId={focusedVenueId}
                  onShowDetail={setDetailVenueId}
                  onGoToEvents={onGoToEvents}
                />
              </Suspense>
            )}

            {tab === "events" && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div role="status" aria-live="polite" className="text-xs text-ink/60">
                    {filteredEvents.length} event{filteredEvents.length === 1 ? "" : "s"}
                  </div>
                  <button
                    type="button"
                    onClick={() => setStackByVenue((s) => !s)}
                    className={`chip text-xs ${stackByVenue ? "chip-active" : ""}`}
                    aria-pressed={stackByVenue}
                    title="Group each venue's events into a single card"
                  >
                    Stack by venue
                  </button>
                </div>
                <p className="text-xs text-ink/60">
                  Looking for galleries? Check{" "}
                  <a
                    href="https://artguide.artforum.com/artguide/place/los-angeles"
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium underline underline-offset-2 hover:text-ink"
                  >
                    ARTFORUM artguide
                  </a>.
                </p>
                <EventList
                  events={filteredEvents}
                  venuesById={venuesById}
                  onShowOnMap={onShowOnMap}
                  onReset={onReset}
                  favs={favs}
                  onToggleFav={toggleFav}
                  stackByVenue={stackByVenue}
                />
              </>
            )}

            {tab === "exhibitions" && (
              <>
                <div role="status" aria-live="polite" className="text-xs text-ink/60">
                  {filteredExhibitions.length} exhibition{filteredExhibitions.length === 1 ? "" : "s"} on view now
                  {filteredExhibitions.length > 0 ? " · ending soonest first" : ""}
                </div>
                <ExhibitionsByVenue
                  exhibitions={filteredExhibitions}
                  venuesById={venuesById}
                  onShowDetail={setDetailVenueId}
                  onReset={onReset}
                  favs={favs}
                  onToggleFav={toggleFav}
                />
              </>
            )}

            {tab === "venues" && (
              <>
                <div role="status" aria-live="polite" className="text-xs text-ink/60">
                  {filteredVenues.length} venue{filteredVenues.length === 1 ? "" : "s"}
                </div>
                <VenueList
                  onReset={onReset}
                  venues={filteredVenues}
                  eventfulIds={eventfulIds}
                  scrapedIds={scrapedIds}
                  onShowOnMap={onShowOnMap}
                  onShowDetail={setDetailVenueId}
                  favs={favs}
                  onToggleFav={toggleFav}
                />
              </>
            )}

            {tab === "archive" && (
              <>
                <div className="panel p-3 text-xs text-ink/60">
                  Archive launched {new Date(ARCHIVE_LAUNCH_DATE).toLocaleDateString(
                    "en-US", { year: "numeric", month: "long", day: "numeric" }
                  )}. Past listings captured by the daily scrape appear here.
                </div>

                {/* Events / Exhibitions toggle (archive holds both) */}
                <div className="flex gap-2">
                  {[["events", "Events"], ["exhibitions", "Exhibitions"]].map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setArchiveMode(key)}
                      className={`chip ${archiveMode === key ? "chip-active" : ""}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div role="status" aria-live="polite" className="text-xs text-ink/60">
                  {filteredArchive.length} past {archiveMode === "exhibitions" ? "exhibition" : "event"}{filteredArchive.length === 1 ? "" : "s"}
                  {filteredArchive.length > 0 ? " (most recent first)" : ""}
                </div>

                {archiveMode === "exhibitions" ? (
                  <ExhibitionsByVenue
                    exhibitions={filteredArchive}
                    venuesById={venuesById}
                    onShowDetail={setDetailVenueId}
                    onReset={onReset}
                    favs={favs}
                    onToggleFav={toggleFav}
                  />
                ) : (
                  <EventList
                    events={filteredArchive}
                    venuesById={venuesById}
                    onReset={onReset}
                    favs={favs}
                    onToggleFav={toggleFav}
                  />
                )}
              </>
            )}

            {tab === "saved" && (
              <>
                {favs.size === 0 ? (
                  <div className="panel p-10 text-center space-y-3 text-sm text-ink/50">
                    <div className="text-3xl">☆</div>
                    <div>Tap the star on any event or venue to save it here.</div>
                  </div>
                ) : (
                  <div className="space-y-8">
                    {savedEvents.length > 0 && (
                      <div>
                        <div role="status" aria-live="polite" className="mb-3 text-xs text-ink/60">
                          {savedEvents.length} saved event{savedEvents.length !== 1 ? "s" : ""}
                        </div>
                        <EventList
                          events={savedEvents}
                          venuesById={venuesById}
                          onShowOnMap={onShowOnMap}
                          grouped={false}
                          favs={favs}
                          onToggleFav={toggleFav}
                        />
                      </div>
                    )}
                    {savedVenues.length > 0 && (
                      <div>
                        <div role="status" aria-live="polite" className="mb-3 text-xs text-ink/60">
                          {savedVenues.length} saved venue{savedVenues.length !== 1 ? "s" : ""}
                        </div>
                        <VenueList
                          venues={savedVenues}
                          eventfulIds={eventfulIds}
                          scrapedIds={scrapedIds}
                          onShowOnMap={onShowOnMap}
                          onShowDetail={setDetailVenueId}
                          favs={favs}
                          onToggleFav={toggleFav}
                        />
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-7xl space-y-2 px-4 pb-10 pt-4 text-xs text-ink/50 md:px-6">
        <p>
          <button
            type="button"
            onClick={() => setAboutOpen(true)}
            className="font-medium text-ink underline-offset-2 hover:underline"
          >
            Something broken, missing, wrong? Let us know!
          </button>
        </p>
        <p>
          {lastUpdated && (
            <>Event data updated {lastUpdated.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}. </>
          )}
          Venue and event data is bot-maintained. Confirm times before heading out!{" "}
          <button type="button" onClick={() => setAboutOpen(true)} className="underline underline-offset-2">About</button>.
          Map tiles © OpenStreetMap contributors · CARTO.
        </p>
      </footer>

      {/* Venue detail panel */}
      <VenueDetail
        venueId={detailVenueId}
        venuesById={venuesById}
        upcomingEvents={upcomingEvents}
        liveExhibitions={liveExhibitions}
        onClose={() => setDetailVenueId(null)}
        onShowOnMap={onShowOnMap}
      />

      {aboutOpen && (
        <AboutDialog
          onClose={() => setAboutOpen(false)}
          onShowArchive={() => setTab("archive")}
        />
      )}
    </div>
  );
}
