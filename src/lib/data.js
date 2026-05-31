// Data loading. Uses `import.meta.env.BASE_URL` so the site works whether
// deployed at site root or at /art-in-la/ on GitHub Pages.

const BASE = import.meta.env.BASE_URL || "/";

async function loadJSON(name) {
  const res = await fetch(`${BASE}data/${name}.json`, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Failed to load ${name}.json: ${res.status}`);
  return res.json();
}

// Guard against duplicate venue IDs in the data file. A stray duplicate would
// otherwise render two map markers for one venue and make the id-keyed detail
// lookup resolve to the wrong record. Keep the most complete record per id.
function dedupeVenues(venues) {
  if (!Array.isArray(venues)) return [];
  const byId = new Map();
  for (const v of venues) {
    if (!v || !v.id) continue;
    const existing = byId.get(v.id);
    if (!existing || Object.keys(v).length > Object.keys(existing).length) {
      byId.set(v.id, v);
    }
  }
  return [...byId.values()];
}

export async function loadAll() {
  const [venues, events, archive, scrapedVenues] = await Promise.all([
    loadJSON("venues"),
    loadJSON("events"),
    loadJSON("archive"),
    loadJSON("scraped_venues").catch(() => []),
  ]);
  return { venues: dedupeVenues(venues), events, archive, scrapedVenues };
}
