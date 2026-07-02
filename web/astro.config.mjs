import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// https://astro.build
export default defineConfig({
  // Swap for the custom domain when there is one.
  site: "https://neon-semifreddo-c99a26.netlify.app",
  integrations: [sitemap()],
  image: {
    // Allow Astro to optimize the RunRepeat product photos at build time.
    domains: ["cdn.runrepeat.com"],
  },
});
