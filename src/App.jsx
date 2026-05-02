import React, {
  lazy, Suspense, useEffect, useMemo, useRef, useState,
} from "react";
import Header from "./components/Header.jsx";
import FilterBar from "./components/FilterBar.jsx";
import EventList from "./components/EventList.jsx";
import VenueList from "./components/VenueList.jsx";
import VenueDetail from "./components/VenueDetail.jsx";
import { loadAll } from "./lib/data.js";
import {
  indexVenues, filterVenues, filterEvents, sortEvents,
  eventfulVenueIds, isUpcoming, partitionByMode, filterExhibitions,
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

// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [data, setData]         = useState({ venues: [], events: [], archive: [], scrapedVenues: [] });

  // Navigation
  const [tab,  setTab]  = useState("map");
  const [mode, setMode] = useState("events");
  const [exhibitionStatus, setExhibitionStatus] = useState("current");

  // Venue-level filters (shared across tabs)
  const [types,   setTypes]   = useState(new Set());
  const [regions, setRegions] = useState(new Set());

  // Event-level filters (Events tab only)
  const [eventTypes,   setEventTypes]   = useState(new Set());
  const [datePreset,   setDatePreset]   = useState("all");
  const [customStart,  setCustomStart]  = useState("");
  const [customEnd,    setCustomEnd]    = useState("");

  // Map filter toggle
  const [mapOnlyEventful, setMapOnlyEventful] = useState(true);

  // Cross-linking: which venue is "focused" on the map
  const [focusedVenueId, setFocusedVenueId] = useState(null);

  // Venue detail panel
  const [detailVenueId, setDetailVenueId] = useState(null);

  // ── URL hash: read on mount ────────────────────────────────────────────────
  const hashInit = useRef(false);
  useEffect(() => {
    if (hashInit.current) return;
    hashInit.current = true;
    const p = readHash();
    if (p.get("tab"))    setTab(p.get("tab"));
    if (p.get("mode"))   setMode(p.get("mode"));
    if (p.get("status")) setExhibitionStatus(p.get("status"));
    if (p.get("types"))  setTypes(new Set(p.get("types").split(",")));
    if (p.get("regions")) setRegions(new Set(p.get("regions").split(",")));
    if (p.get("etypes")) setEventTypes(new Set(p.get("etypes").split(",")));
    if (p.get("date"))   setDatePreset(p.get("date"));
    if (p.get("from"))   setCustomStart(p.get("from"));
    if (p.get("to"))     setCustomEnd(p.get("to"));
    if (p.get("map"))    setMapOnlyEventful(p.get("map") !== "all");
  }, []);

  // ── URL hash: write on state change ───────────────────────────────────────
  useEffect(() => {
    if (!hashInit.current) return;
    const p = new URLSearchParams();
    p.set("tab", tab);
    if (mode !== "events") p.set("mode", mode);
    if (exhibitionStatus !== "current") p.set("status", exhibitionStatus);
    if (types.size)   p.set("types",   [...types].join(","));
    if (regions.size) p.set("regions", [...regions].join(","));
    if (eventTypes.size) p.set("etypes", [...eventTypes].join(","));
    if (datePreset && datePreset !== "all") p.set("date", datePreset);
    if (customStart) p.set("from", customStart);
    if (customEnd)   p.set("to",   customEnd);
    if (!mapOnlyEventful) p.set("map", "all");
    writeHash(p);
  }, [tab, mode, exhibitionStatus, types, regions, eventTypes, datePreset, customStart, customEnd, mapOnlyEventful]);

  // ── Data load ─────────────────────────────────────────────────────────────
  useEffect(() => {
    loadAll()
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, []);

  // ── Derived data ──────────────────────────────────────────────────────────
  const venuesById  = useMemo(() => indexVenues(data.venues),   [data.venues]);
  const scrapedIds  = useMemo(() => new Set(data.scrapedVenues || []), [data.scrapedVenues]);

  const { oneoff: allOneoff, exhibitions: allExhibitions } = useMemo(
    () => partitionByMode(data.events), [data.events]
  );
  const upcomingEvents  = useMemo(() => allOneoff.filter(isUpcoming),      [allOneoff]);
  const liveExhibitions = useMemo(() => allExhibitions.filter(isUpcoming), [allExhibitions]);
  const eventfulIds     = useMemo(() => eventfulVenueIds(upcomingEvents),  [upcomingEvents]);

  // Map shows all or eventful-only depending on toggle
  const eventfulFilter = tab === "map" && mapOnlyEventful;

  const filteredVenues = useMemo(
    () => filterVenues(data.venues, { types, regions, eventful: eventfulFilter, eventfulIds }),
    [data.venues, types, regions, eventfulFilter, eventfulIds]
  );

  const filteredEvents = useMemo(
    () => sortEvents(filterEvents(upcomingEvents, venuesById, {
      venueTypes: types, eventTypes, regions,
      datePreset: datePreset !== "custom" ? datePreset : "all",
      startDate: datePreset === "custom" ? customStart : undefined,
      endDate:   datePreset === "custom" ? customEnd   : undefined,
    })),
    [upcomingEvents, venuesById, types, eventTypes, regions, datePreset, customStart, customEnd]
  );

  const filteredExhibitions = useMemo(
    () => sortEvents(filterEvents(
      filterExhibitions(liveExhibitions, exhibitionStatus),
      venuesById, { venueTypes: types, regions }
    )),
    [liveExhibitions, exhibitionStatus, venuesById, types, regions]
  );

  const filteredArchive = useMemo(
    () => sortEvents(filterEvents(data.archive, venuesById, {
      venueTypes: types, eventTypes, regions, datePreset,
    })).reverse(),
    [data.archive, venuesById, types, eventTypes, regions, datePreset]
  );

  // ── Callbacks ─────────────────────────────────────────────────────────────
  const onReset = () => {
    setTypes(new Set());
    setEventTypes(new Set());
    setRegions(new Set());
    setDatePreset("all");
    setCustomStart("");
    setCustomEnd("");
    setExhibitionStatus("current");
  };

  /** "Show on map": fly to venue and switch to map tab. */
  const onShowOnMap = (venueId) => {
    setFocusedVenueId(null);               // reset first so effect re-fires
    setTimeout(() => setFocusedVenueId(venueId), 0);
    setTab("map");
  };

  /** "See events →" from map popup: switch to Events tab. */
  const onGoToEvents = (venueId) => {
    setMode("events");
    setTab("events");
  };

  const stats = {
    venues:      data.venues.length,
    events:      upcomingEvents.length,
    exhibitions: liveExhibitions.length,
  };

  const inExhibitionMode = mode === "exhibitions";
  const eventsTabList    = inExhibitionMode ? filteredExhibitions : filteredEvents;
  const eventsTabNoun    = inExhibitionMode ? "exhibition" : "event";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      <Header tab={tab} setTab={setTab} stats={loading ? null : stats} />

      <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {error && (
          <div className="panel p-6 text-center text-sm text-red-700">{error}</div>
        )}

        {/* FilterBar always visible (even while loading) */}
        <FilterBar
          tab={tab} mode={mode} setMode={setMode}
          types={types} setTypes={setTypes}
          eventTypes={eventTypes} setEventTypes={setEventTypes}
          regions={regions} setRegions={setRegions}
          datePreset={datePreset} setDatePreset={setDatePreset}
          customStart={customStart} setCustomStart={setCustomStart}
          customEnd={customEnd}     setCustomEnd={setCustomEnd}
          exhibitionStatus={exhibitionStatus} setExhibitionStatus={setExhibitionStatus}
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
                <div className="text-xs text-ink/60">
                  {eventsTabList.length} {eventsTabNoun}{eventsTabList.length === 1 ? "" : "s"}
                </div>
                <EventList
                  events={eventsTabList}
                  venuesById={venuesById}
                  onShowOnMap={onShowOnMap}
                />
              </>
            )}

            {tab === "venues" && (
              <>
                <div className="text-xs text-ink/60">
                  {filteredVenues.length} venue{filteredVenues.length === 1 ? "" : "s"}
                </div>
                <VenueList
                  venues={filteredVenues}
                  eventfulIds={eventfulIds}
                  scrapedIds={scrapedIds}
                  onShowOnMap={onShowOnMap}
                  onShowDetail={setDetailVenueId}
                />
              </>
            )}

            {tab === "archive" && (
              <>
                <div className="panel p-3 text-xs text-ink/60">
                  Archive launched {new Date(ARCHIVE_LAUNCH_DATE).toLocaleDateString(
                    "en-US", { year: "numeric", month: "long", day: "numeric" }
                  )}. Past events captured by the daily scrape will appear here.
                </div>
                <div className="text-xs text-ink/60">
                  {filteredArchive.length} past event{filteredArchive.length === 1 ? "" : "s"}
                  {filteredArchive.length > 0 ? " (most recent first)" : ""}
                </div>
                <EventList events={filteredArchive} venuesById={venuesById} />
              </>
            )}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 pt-4 text-xs text-ink/50 md:px-6">
        Venue and event data is community-maintained.
        Map tiles © OpenStreetMap contributors · CARTO.{" "}
        <a href="https://github.com/birdofnofeather/art-in-la" className="underline">
          Contribute on GitHub
        </a>.
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
    </div>
  );
}
