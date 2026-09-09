import react from "@vitejs/plugin-react";
import { defineConfig, splitVendorChunkPlugin } from "vite";
import svgr from "vite-plugin-svgr";
import { visualizer } from "rollup-plugin-visualizer";
import tsconfigPaths from "vite-tsconfig-paths";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    tsconfigPaths(),
    react({
      include: "**/*.tsx",
    }),
    svgr(),
    // bundle analysis is memory-hungry and only useful when manually
    // inspecting bundle size; skip it on normal/production builds
    ...(process.env.ANALYZE ? [visualizer()] : []),
    splitVendorChunkPlugin(),
  ],
  build: {
    // gzip-size reporting for every chunk adds noticeable memory/time
    // on low-RAM build hosts and isn't needed outside local inspection
    reportCompressedSize: false,
  },
});
