// Shareable links to a single event or exhibition: <site>/#event=<id>.
// App.jsx reads the param on load, switches to the right tab with filters
// cleared, scrolls to the item and highlights it.

export function eventLink(ev) {
  const base = window.location.origin + window.location.pathname;
  return `${base}#event=${encodeURIComponent(ev.id)}`;
}

/** Native share sheet where available (phones), else copy to clipboard.
    Resolves to "shared" | "copied" | "failed". */
export async function shareEvent(ev, venueName) {
  const url = eventLink(ev);
  const title = ev.title || "Event";
  try {
    if (navigator.share) {
      await navigator.share({ title, text: venueName ? `${title} — ${venueName}` : title, url });
      return "shared";
    }
  } catch (e) {
    if (e && e.name === "AbortError") return "failed";   // user closed the sheet
  }
  try {
    await navigator.clipboard.writeText(url);
    return "copied";
  } catch {
    window.prompt("Copy this link:", url);   // last resort (old browsers / no permission)
    return "copied";
  }
}
