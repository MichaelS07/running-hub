import { defineConfig } from "astro/config";

// https://astro.build
export default defineConfig({
  // Update to your real domain once deployed (used for sitemaps / canonical URLs).
  site: "https://runhub.example.com",
  image: {
    // Allow Astro to optimize the RunRepeat product photos at build time.
    domains: ["cdn.runrepeat.com"],
  },
});
