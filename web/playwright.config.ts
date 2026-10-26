// Playwright - end-to-end flows against a running stack (docker compose up -> :8080).
// Locally it drives the Edge that ships with Windows, so no browser download is needed;
// CI sets E2E_CHANNEL="" and uses the bundled Chromium.
//
// Projects: "e2e" (pnpm e2e) checks the flows; "screenshots" (pnpm screenshots) refreshes
// the images in docs/screenshots used by the README.

import { defineConfig } from "@playwright/test";

const channel = process.env.E2E_CHANNEL ?? (process.platform === "win32" ? "msedge" : "");

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  // The flows share the demo database (drivers, offers), so they run one after another.
  workers: 1,
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    channel: channel || undefined,
    viewport: { width: 1280, height: 860 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "e2e", testMatch: "**/*.e2e.ts" },
    { name: "screenshots", testMatch: "**/*.capture.ts" },
  ],
});
