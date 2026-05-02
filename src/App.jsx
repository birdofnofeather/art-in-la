import React, { useEffect, useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import FilterBar from "./components/FilterBar.jsx";
import VenueMap from "./components/VenueMap.jsx";
import EventList from "./components/EventList.jsx";
import VenueList from "./components/VenueList.jsx";
import { loadAll } from "./lib/data.js";
import {
  indexVenues, filterVenues, filterEvents, sortEvents, eventfulVenueIds,
  isUpcoming, partitionByMode, filterExhibitions,
} from "./lib/filters.js";
import { ARCHIVE_LAUNCH_DATE } from "./lib/constants.js";

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({ venues: [], events: [], archive: [] });

  const [tab, setTab] = useState("map");
  const [mode, setMode] = useState("events"); // "events" | "exhibitions"
  const [exhibitionStatus, setExhibitionStatus] = useState("current"); // "current" | "upcoming" | "all"

  const [types, setTypes] = useState(new Set());
  const [eventTypes, setEventTypes] = useState(new Set());
  const [regions, setRegions] = useState(new Set());
  const [datePreset, setDatePreset] = useState("all");

  useEffect(() => {
    loadAll()
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, []);

  const venuesById = useMemo(() => indexVenues(data.venues), [data.venues]);

  // Split the data set once so the rest of the app can pick the right slice.
  const { oneoff: allOneoff, exhibitions: allExhibitions } = useMemo(
    () => partitionByMode(data.events),
    [data.events]
  );

  const upcomingEvents = useMemo(
    () => allOneoff.filter((e) => isUpcoming(e)),
    [allOneoff]
  );
  const liveExhibitions = useMemo(
    () => allExhibitions.filter((e) => isUpcoming(e)),
    [allExhibitions]
  );
  const eventfulIds = useMemo(() => eventfulVenueIds(upcomingEvents), [upcomingEvents]);

  // Map filter toggle — default ON (show only venues with upcoming events).
  const [mapOnlyEventful, setMapOnlyEventful] = useState(true);

  // Map view respects the toggle; Venues tab always shows the full database.
  const eventfulFilter = tab === "map" && mapOnlyEventful;

  const filteredVenues = useMemo(
    () => filterVenues(data.venues, {
      types, regions,
      eventful: eventfulFilter,
      eventfulIds,
    }),
    [data.venues, types, regions, eventfulFilter, eventfulIds]
  );

  const filteredEvents = useMemo(
    () => sortEvents(filterEvents(upcomingEvents, venuesById, {
      venueTypes: types, eventTypes, regions, datePreset,
    })),
    [upcomingEvents, venuesById, types, eventTypes, regions, datePreset]
  );

  const filteredExhibitions = useMemo(() => {
    const matching = filterExhibitions(liveExhibitions, exhibitionStatus);
    return sortEvents(filterEvents(matching, venuesById, {
      venueTypes: types, regions,
      // Don't apply eventTypes here — exhibitions only have one type.
      // Don't apply datePreset — exhibition view has its own status selector.
    }));
  }, [liveExhibitions, exhibitionStatus, venuesById, types, regions]);

  const filteredArchive = useMemo(
    () => sortEvents(filterEvents(data.archive, venuesById, {
      venueTypes: types, eventTypes, regions, datePreset,
    })).reverse(),
    [data.archive, venuesById, types, eventTypes, regions, datePreset]
  );

  const onReset = () => {
    setTypes(new Set());
    setEventTypes(new Set());
    setRegions(new Set());
    setDatePreset("all");
    setExhibitionStatus("current");
  };

  const stats = {
    venues: data.venues.length,
    events: upcomingEvents.length,
    exhibitions: liveExhibitions.length,
  };

  // Which list does the Events tab show?
  const inExhibitionMode = mode === "exhibitions";
  const eventsTabList = inExhibitionMode ? filteredExhibitions : filteredEvents;
  const eventsTabNoun = inExhibitionMode ? "exhibition" : "event";

  return (
    <div className="min-h-screen">
      <Header tab={tab} setTab={setTab} mode={mode} setMode={setMode} stats={stats} />
      <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
        {loading && (
          <div className="panel p-6 text-center text-sm text-ink/60">
            Loading data…
          </div>
        )}
        {error && (
          <div className="panel p-6 text-center text-sm text-red-700">{error}</div>
        )}

        {!loading && !error && (
          <>
            <FilterBar
              tab={tab}
              mode={mode}
              types={types} setTypes={setTypes}
              eventTypes={eventTypes} setEventTypes={setEventTypes}
              regions={regions} setRegions={setRegions}
              datePreset={datePreset} setDatePreset={setDatePreset}
              exhibitionStatus={exhibitionStatus} setExhibitionStatus={setExhibitionStatus}
              onReset={onReset}
            />

            {tab === "map" && (
              <VenueMap
                venues={filteredVenues}
                eventfulIds={eventfulIds}
                onlyEventful={mapOnlyEventful}
                setOnlyEventful={setMapOnlyEventful}
              />
            )}
            {tab === "events" && (
              <>
                <div className="text-xs text-ink/60">
                  {eventsTabList.length} {eventsTabNoun}{eventsTabList.length === 1 ? "" : "s"}
                </div>
                <EventList events={eventsTabList} venuesById={venuesById} />
              </>
            )}
            {tab === "venues" && (
              <>
                <div className="text-xs text-ink/60">
                  {filteredVenues.length} venue{filteredVenues.length === 1 ? "" : "s"}
                </div>
                <VenueList venues={filteredVenues} eventfulIds={eventfulIds} />
              </>
            )}
            {tab === "archive" && (
              <>
                <div className="panel p-3 text-xs text-ink/60">
                  Archive launched {new Date(ARCHIVE_LAUNCH_DATE).toLocaleDateString(
                    "en-US",
                    { year: "numeric", month: "long", day: "numeric" }
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
        Map tiles © OpenStreetMap contributors · CARTO.
        {" "}
        <a href="https://github.com/birdofnofeather/art-in-la" className="underline">
          Contribute on GitHub
        </a>
        .
      </footer>
    </div>
  );
}
