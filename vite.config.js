import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  root: ".",
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      input: path.resolve(__dirname, "react-preview.html"),
    },
  },
  server: {
    open: "/react-preview.html",
    // Proxy API calls to the FastAPI backend so we avoid CORS issues in dev
    proxy: {
      "/recommend": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
