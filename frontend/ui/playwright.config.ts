import { defineConfig, devices } from '@playwright/test';

// E2E runs the built app against a real seeded backend (see docs/planning/ENVIRONMENT.md).
// If Playwright browsers cannot be downloaded in the environment (G-P5b), E2E degrades to
// Testing-Library + MSW integration coverage; this config stays as the executable spec.
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : {
        // Serve a built app via `vite preview` (no file watchers — avoids the env's EMFILE
        // limit). Intercept the API in-browser (MSW) so the full flow runs deterministically
        // without a live backend. Live-SSE isn't reliably mockable in a service worker; it's
        // covered by the R3 hook/reducer unit tests.
        command: 'pnpm run e2e:serve',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        env: { VITE_E2E_MOCK: '1' },
      },
});
