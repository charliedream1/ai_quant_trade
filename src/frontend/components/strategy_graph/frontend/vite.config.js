import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "../assets",
    emptyOutDir: false,
    lib: {
      entry: "src/index.ts",
      formats: ["es"],
      fileName: () => "graph.js",
      cssFileName: "graph",
    },
    sourcemap: false,
  },
});
