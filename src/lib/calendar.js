// Build calendar artifacts from an event + its venue.
// Event shape: { title, description, start, end, all_day, url, location_override }
// Venue: { name, address }

function pad(n) { return String(n).padStart(2, "0"); }

/** Format a Date as an ICS UTC timestamp: 20260612T190000Z */
function toICSDate(d) {
  return (
    d.getUTCFullYear() +
    pad(d.getUTCMonth() + 1) +
    pad(d.getUTCDate()) + "T" +
    pad(d.getUTCHours()) +
    pad(d.getUTCMinutes()) +
    pad(d.getUTCSeconds()) + "Z"
  );
}

/** Format a Date as an all-day ICS date value: 20260612 */
function toICSDateOnly(d) {
  return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate());
}

function escapeICS(text = "") {
  return String(text)
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\n/g, "\\n");
}

function locationFor(ev, venue) {
  return ev.location_override || venue?.address || venue?.name || "";
}

/** Returns the full text of a .ics file for a single event, or null if it has
 *  no usable start date. */
export function buildICS(ev, venue) {
  const start = ev.start ? new Date(ev.start) : null;
  if (!start || Number.isNaN(+start)) return null;
  const end = ev.end ? new Date(ev.end) : null;
  const endValid = end && !Number.isNaN(+end);

  const allDay = !!ev.all_day || (typeof ev.start === "string" && !ev.start.includes("T"));

  let dtStart, dtEnd;
  if (allDay) {
    dtStart = `DTSTART;VALUE=DATE:${toICSDateOnly(start)}`;
    // ICS all-day DTEND is exclusive — add a day if no explicit end.
    const e = endValid ? end : new Date(start.getTime() + 864e5);
    dtEnd = `DTEND;VALUE=DATE:${toICSDateOnly(e)}`;
  } else {
    dtStart = `DTSTART:${toICSDate(start)}`;
    const e = endValid ? end : new Date(start.getTime() + 2 * 3600e3); // default 2h
    dtEnd = `DTEND:${toICSDate(e)}`;
  }

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Art in LA//EN",
    "CALSCALE:GREGORIAN",
    "BEGIN:VEVENT",
    `UID:${ev.id}@art-in-la`,
    `DTSTAMP:${toICSDate(new Date())}`,
    dtStart,
    dtEnd,
    `SUMMARY:${escapeICS(ev.title)}`,
    ev.description ? `DESCRIPTION:${escapeICS(ev.description)}` : null,
    `LOCATION:${escapeICS(locationFor(ev, venue))}`,
    ev.url ? `URL:${escapeICS(ev.url)}` : null,
    "END:VEVENT",
    "END:VCALENDAR",
  ].filter(Boolean);

  // ICS spec requires CRLF line endings.
  return lines.join("\r\n");
}

/** Trigger a download of the .ics for an event. */
export function downloadICS(ev, venue) {
  const ics = buildICS(ev, venue);
  if (!ics) return;
  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${ev.id || "event"}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Google Calendar "add event" URL. */
export function googleCalUrl(ev, venue) {
  const start = ev.start ? new Date(ev.start) : null;
  if (!start || Number.isNaN(+start)) return null;
  const end = ev.end && !Number.isNaN(+new Date(ev.end))
    ? new Date(ev.end)
    : new Date(start.getTime() + 2 * 3600e3);

  const allDay = !!ev.all_day || (typeof ev.start === "string" && !ev.start.includes("T"));
  const dates = allDay
    ? `${toICSDateOnly(start)}/${toICSDateOnly(new Date(end.getTime() + 864e5))}`
    : `${toICSDate(start)}/${toICSDate(end)}`;

  const p = new URLSearchParams({
    action: "TEMPLATE",
    text: ev.title || "",
    dates,
    details: [ev.description, ev.url].filter(Boolean).join("\n\n"),
    location: locationFor(ev, venue),
  });
  return `https://calendar.google.com/calendar/render?${p.toString()}`;
}
