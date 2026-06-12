import { useCallback, useEffect, useState } from "react";

const KEY = "artinla:favorites:v1";

function read() {
  try { return new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); }
  catch { return new Set(); }
}

/** Favorites are stored as a flat Set of string ids. Event ids and venue ids
 *  share one namespace — they're already globally unique slugs/hashes. */
export function useFavorites() {
  const [favs, setFavs] = useState(read);

  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify([...favs])); } catch {}
  }, [favs]);

  // Keep multiple tabs in sync.
  useEffect(() => {
    const onStorage = (e) => { if (e.key === KEY) setFavs(read()); };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = useCallback((id) => {
    setFavs((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const has = useCallback((id) => favs.has(id), [favs]);

  return { favs, has, toggle };
}
