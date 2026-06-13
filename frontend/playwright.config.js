import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E configuration for the WoniuNote Vue 3 frontend.
 *
 * Approach: tests run against the production build served by `vite preview`.
 * Backend API calls are intercepted with Playwright route mocks (see
 * e2e/support/mockApi.js), so the suite is deterministic and needs no live
 * C++ backend, MySQL or Redis. This exercises the real router, rendering and
 * user interaction paths — the parts a unit test cannot cover — while keeping
 * runs hermetic and CI-friendly.
 *
 * To run against a real backend instead, set E2E_BASE_URL to its origin and
 * remove the per-test route mocks.
 */
const PORT = process.env.E2E_PORT || 4173
const BASE_URL = process.env.E2E_BASE_URL || `http://127.0.0.1:${PORT}`

// Which browser projects to run. Default to chromium-only locally (so a bare
// `npx playwright install chromium` is enough); set PW_BROWSERS=all in CI to
// run the full desktop + mobile matrix. Comma-separated subsets also work,
// e.g. PW_BROWSERS=chromium,firefox.
const requested = (process.env.PW_BROWSERS || 'chromium').toLowerCase()
const wantAll = requested === 'all'
const wants = (name) => wantAll || requested.split(',').map((s) => s.trim()).includes(name)

const chromiumLaunch = process.env.PW_CHROMIUM_PATH
  ? { executablePath: process.env.PW_CHROMIUM_PATH }
  : {}

const allProjects = [
  {
    name: 'chromium',
    use: {
      ...devices['Desktop Chrome'],
      // Use the full Chromium build rather than the separate headless-shell
      // binary. Allows running with only `npx playwright install chromium`.
      // Override with PW_CHROMIUM_PATH if your install lives elsewhere.
      channel: undefined,
      launchOptions: chromiumLaunch
    }
  },
  { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  // Mobile viewport (Chromium engine) to catch responsive regressions.
  { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } }
]

const projects = allProjects.filter((p) => wants(p.name))

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.js',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: projects.length > 0 ? projects : [allProjects[0]],
  // Build once, then serve the static build for fast, production-like E2E.
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${PORT} --strictPort`,
        url: BASE_URL,
        timeout: 180000,
        reuseExistingServer: !process.env.CI
      }
})
