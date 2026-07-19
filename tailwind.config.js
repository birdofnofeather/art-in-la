/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Org type palette — used on venue cards and filter chips (not map).
        venue: {
          museum: "#1c1917",        // warm near-black
          community: "#15803d",     // green-700
          alternative: "#7c3aed",   // violet-600
          academic: "#b45309",      // amber-700
        },
        ink: "#1c1917",             // warm near-black (stone-900)
        paper: "#f6f4ef",           // warm gallery off-white
        card: "#fffdf8",            // panel surface, slightly warm
        accent: "#b5442c",          // terracotta — links, markers, highlights
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(28,25,23,.05), 0 1px 8px rgba(28,25,23,.04)",
      },
    },
  },
  plugins: [],
};
