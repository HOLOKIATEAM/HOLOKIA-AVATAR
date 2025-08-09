import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import dtsPlugin from "vite-plugin-dts";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    dtsPlugin({
      insertTypesEntry: true,
      rollupTypes: true,
    }),
  ],
  build: {
    lib: {
      entry: "src/index.ts",
      name: "Wawa-lipsync",
      fileName: (format) => `wawa-lipsync.${format}.js`,
    },
    rollupOptions: {
      external: [], // Don't bundle these
      output: {
        globals: {},
      },
    },
  },
});
