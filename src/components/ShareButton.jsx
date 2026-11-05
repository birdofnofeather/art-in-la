import React, { useState } from "react";
import { shareEvent } from "../lib/share.js";

export function ShareIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><path d="M16 6l-4-4-4 4" /><path d="M12 2v13" />
    </svg>
  );
}

/** Icon button: share (phone) or copy link (desktop), with a brief status. */
export default function ShareButton({ ev, venueName, className = "" }) {
  const [status, setStatus] = useState(null);
  const onClick = async () => {
    const r = await shareEvent(ev, venueName);
    if (r === "copied") { setStatus("Link copied"); setTimeout(() => setStatus(null), 2000); }
  };
  return (
    <span className="relative inline-flex">
      <button type="button" onClick={onClick} aria-label={`Share ${ev.title}`} title="Share"
        className={`icon-btn ${className}`}>
        <ShareIcon />
      </button>
      {status && (
        <span role="status" className="absolute bottom-full left-1/2 mb-1 -translate-x-1/2 whitespace-nowrap rounded bg-ink px-2 py-0.5 text-xs text-white">
          {status}
        </span>
      )}
    </span>
  );
}
