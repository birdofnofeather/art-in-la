import React, { useEffect, useRef, useState } from "react";

const WEB3FORMS_KEY = "758cf396-a5fe-4378-93c6-b4360b5632eb";

function FeedbackForm() {
  const [status, setStatus] = useState("idle"); // idle | sending | ok | error
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setStatus("sending");
    setError("");
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    try {
      const res = await fetch("https://api.web3forms.com/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ access_key: WEB3FORMS_KEY, ...data }),
      });
      const json = await res.json();
      if (json.success) { setStatus("ok"); form.reset(); }
      else { setStatus("error"); setError(json.message || "Something went wrong."); }
    } catch (err) {
      setStatus("error");
      setError(String(err));
    }
  }

  if (status === "ok") {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
        Thanks — your message was sent. 🙏
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <input type="hidden" name="subject" value="Art in LA — feedback" />
      {/* Honeypot */}
      <input type="checkbox" name="botcheck" tabIndex={-1} className="hidden" aria-hidden />
      <textarea
        name="message"
        required
        rows={3}
        placeholder="Something broken, missing, or wrong? Tell us what you saw…"
        className="w-full rounded-md border border-black/15 px-3 py-2 text-sm focus:border-ink/40 focus:outline-none"
      />
      <input
        type="email"
        name="email"
        placeholder="Your email (optional, only if you'd like a reply)"
        className="w-full rounded-md border border-black/15 px-3 py-2 text-sm focus:border-ink/40 focus:outline-none"
      />
      {status === "error" && (
        <p className="text-xs text-red-600">Couldn’t send: {error}</p>
      )}
      <button
        type="submit"
        disabled={status === "sending"}
        className="chip chip-active disabled:opacity-60"
      >
        {status === "sending" ? "Sending…" : "Send message"}
      </button>
    </form>
  );
}

function SubscribeSection() {
  const base = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const feeds = [
    { key: "all", label: "All events" },
    { key: "free", label: "Free events" },
    { key: "family", label: "Family-friendly" },
  ];
  const [copied, setCopied] = useState("");
  const copy = async (url, key) => {
    try { await navigator.clipboard.writeText(url); setCopied(key); setTimeout(() => setCopied(""), 1500); }
    catch { /* clipboard blocked — the link is still selectable */ }
  };
  return (
    <div className="space-y-2 border-t border-black/10 pt-4">
      <h3 className="text-sm font-semibold">Subscribe in your calendar</h3>
      <p className="text-xs text-ink/60">
        Add a live feed once and new listings appear automatically. In Google
        Calendar: <em>Other calendars → From URL</em>. In Apple Calendar:{" "}
        <em>File → New Calendar Subscription</em>.
      </p>
      <div className="space-y-1.5">
        {feeds.map((f) => {
          const url = `${origin}${base}/data/feeds/${f.key}.ics`;
          return (
            <div key={f.key} className="flex items-center gap-2">
              <span className="w-28 shrink-0 text-xs font-medium">{f.label}</span>
              <code className="min-w-0 flex-1 truncate rounded bg-black/5 px-2 py-1 text-xs text-ink/70">{url}</code>
              <button type="button" onClick={() => copy(url, f.key)} className="chip text-xs">
                {copied === f.key ? "Copied" : "Copy"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AboutDialog({ onClose, onShowArchive }) {
  const panelRef = useRef(null);
  const openerRef = useRef(null);

  useEffect(() => {
    openerRef.current = document.activeElement;
    const t = setTimeout(() => {
      panelRef.current?.querySelector("button, [href], textarea, input")?.focus();
    }, 0);
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(t);
      window.removeEventListener("keydown", onKey);
      openerRef.current?.focus?.();
    };
  }, [onClose]);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center">
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="about-heading"
          className="panel w-full max-w-lg space-y-5 p-6"
        >
          <div className="flex items-start justify-between gap-3">
            <h2 id="about-heading" className="font-display text-xl font-bold">About Art in LA</h2>
            <button
              type="button" onClick={onClose} aria-label="Close"
              className="shrink-0 rounded-full p-1.5 text-ink/50 hover:bg-black/5 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* How it works */}
          <div className="space-y-2 text-sm text-ink/70">
            <p>
              A free map and calendar of exhibitions and events at Los Angeles’s
              museums and non-commercial art spaces — no galleries, no ticket
              sellers.
            </p>
            <p>
              Listings are gathered automatically: a bot visits each venue’s
              website once a day and copies what it finds. Browse the{" "}
              <strong>Map</strong>, scan one-off <strong>Events</strong>, see what’s
              on view under <strong>Exhibitions</strong>, or star things to keep them
              under <strong>Saved</strong>. All times are Los Angeles local.
            </p>
            <p className="text-ink/60">
              Because it’s bot-maintained, details can lag or be wrong —
              confirm with the venue before heading out.
            </p>
            {onShowArchive && (
              <button
                type="button"
                onClick={() => { onShowArchive(); onClose(); }}
                className="text-ink underline-offset-2 hover:underline"
              >
                Browse the archive of past listings →
              </button>
            )}
          </div>

          <SubscribeSection />

          {/* Feedback */}
          <div className="space-y-2 border-t border-black/10 pt-4">
            <h3 className="text-sm font-semibold">Something broken, missing, wrong? Let us know!</h3>
            <FeedbackForm />
          </div>
        </div>
      </div>
    </>
  );
}
