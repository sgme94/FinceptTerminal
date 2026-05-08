/// <reference types="vitest" />

import { defineConfig } from "vite";
import type { UserConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    include: ["src/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts"
  },
  server: {
    host: "127.0.0.1",
    port: 4177,
    strictPort: true
  }
} as UserConfig & { test: { include: string[]; environment: "jsdom"; setupFiles: string } });
