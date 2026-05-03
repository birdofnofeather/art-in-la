// Data loading. Uses `import.meta.env.BASE_URL` so the site works whether
// deployed at site root or at /art-in-la/ on GitHub Pages.

const BASE = import.meta.env.BASE_URL || "/";

async function loadJSON(name) {
  const res = await fetch(`${BASE}data/${name}.json`, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Failed to load ${name}.json: ${res.status}`);
  return res.json();
}

export async function loadAll() {
  const [venues, events, archive, scrapedVenues] = await Promise.all([
    loadJSON("venues"),
    loadJSON("events"),
    loadJSON("archive"),
    loadJSON("scraped_venues").catch(() => []),
  ]);
  return { venues, events, archive, scrapedVenues };
}
