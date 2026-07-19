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

const RESOURCES = [
  {
    group: "Also covering visual art",
    items: [
      { name: "ARTFORUM artguide", url: "https://artguide.artforum.com/artguide/place/los-angeles", blurb: "commercial galleries + museums" },
      { name: "Curate LA", url: "https://curate.la/", blurb: "gallery openings, the scene" },
      { name: "Mommy Poppins LA", url: "https://mommypoppins.com/los-angeles-kids", blurb: "kids & family activities" },
      { name: "LAist: Things to Do", url: "https://laist.com/best-things-to-do", blurb: "editorial picks of the week" },
    ],
  },
  {
    group: "Performing arts",
    items: [
      { name: "Stage Raw", url: "https://stageraw.com/stage-listings/", blurb: "independent LA theater" },
      { name: "BroadwayWorld LA", url: "https://www.broadwayworld.com/los-angeles/regionalshows/", blurb: "touring & regional shows" },
      { name: "Theater.Guide LA", url: "https://theater.guide/city/los-angeles/", blurb: "searchable stage calendar" },
    ],
  },
];

function ResourcesSection() {
  return (
    <div className="space-y-3 border-t border-black/10 pt-4">
      <h3 className="text-sm font-semibold">Looking for something else?</h3>
      {RESOURCES.map((g) => (
        <div key={g.group} className="space-y-1.5">
          <div className="text-xs font-semibold uppercase tracking-wider text-ink/60">{g.group}</div>
          <ul className="space-y-0.5 text-xs text-ink/70">
            {g.items.map((r) => (
              <li key={r.name}>
                <a href={r.url} target="_blank" rel="noreferrer" className="font-medium text-ink underline underline-offset-2 hover:text-accent">
                  {r.name}
                </a>{" "}
                — {r.blurb}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}


export default function AboutDialog({ onClose }) {
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
      <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 py-8">
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="about-heading"
          className="panel my-auto max-h-[calc(100vh-4rem)] w-full max-w-lg space-y-5 overflow-y-auto p-6"
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

          {/* What this is */}
          <div className="space-y-2 text-sm text-ink/70">
            <p>
              <strong>The visual-art calendar for LA County.</strong> Every museum,
              community art center, university gallery, and artist-run space —
              their exhibitions, openings, screenings, talks, and workshops, in
              one free place. No accounts, no ads, no ticket-seller noise.
            </p>
            <p>
              What we deliberately leave out: <em>commercial galleries</em> (see
              the guides below — they cover that world well) and{" "}
              <em>performing-arts venues</em> — theater, opera, and dance have
              their own calendars, also linked below. Museum film screenings and
              performances <em>inside</em> art venues are included.
            </p>
            <p>
              Listings are gathered automatically: a bot reads each venue's own
              website daily, so coverage doesn't depend on anyone remembering to
              submit an event. All times are LA-local. Details can occasionally
              lag or misread — confirm with the venue before heading out.
            </p>
          </div>

          <ResourcesSection />

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
