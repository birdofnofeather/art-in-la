/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Org type palette — used on map markers and chips.
        venue: {
          museum: "#0f172a",        // slate-900
          gallery: "#b91c1c",       // red-700
          community: "#15803d",     // green-700
          alternative: "#7c3aed",   // violet-600
          academic: "#b45309",      // amber-700
        },
        ink: "#111111",
        paper: "#fafafa",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
