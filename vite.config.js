import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// For GitHub Pages project sites the site lives under /<repo-name>/.
// Set VITE_BASE_PATH=/art-in-la/ (or the repo's name) at build time.
// For user/organization sites (username.github.io) or Vercel, leave it "/".
const base = process.env.VITE_BASE_PATH || "/";

export default defineConfig({
  base,
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
