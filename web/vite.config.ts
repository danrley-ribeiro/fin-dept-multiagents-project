/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api vai para o servidor Python (`python -m fin_mas serve`).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8765", changeOrigin: false } },
  },
  build: {
    rollupOptions: {
      output: { manualChunks: { react: ["react", "react-dom"], mui: ["@mui/material", "@emotion/react", "@emotion/styled"] } },
    },
  },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
