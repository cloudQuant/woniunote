import { defineConfig, devices } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

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
 * This config is exclusively for route-mocked tests. Real-backend tests use
 * their isolated configuration and must never bypass the mock preview guard.
 */
if (process.env.E2E_BASE_URL) {
  throw new Error('Mock E2E refuses E2E_BASE_URL; use the isolated real-backend Playwright config')
}
if (process.env.WONIUNOTE_REAL_E2E === '1' || process.env.WONIUNOTE_API_PROXY_TARGET) {
  throw new Error('Mock E2E refuses real-backend proxy configuration')
}

const PORT = process.env.E2E_PORT || 4173
const BASE_URL = `http://127.0.0.1:${PORT}`
// Playwright worker processes import this config again. Preserve the run ID
// and path inherited from the runner so their context audits are read by the
// same global teardown gate instead of being split across per-worker logs.
if (!process.env.WONIUNOTE_MOCK_EGRESS_RUN_ID) {
  process.env.WONIUNOTE_MOCK_EGRESS_RUN_ID = randomUUID()
  process.env.WONIUNOTE_MOCK_EGRESS_LOG = join(
    tmpdir(),
    `woniunote-mock-egress-${process.pid}-${process.env.WONIUNOTE_MOCK_EGRESS_RUN_ID}.json`
  )
}
if (!process.env.WONIUNOTE_MOCK_EGRESS_LOG) {
  throw new Error('Mock E2E run ID exists without an egress audit path')
}

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
  globalTeardown: './e2e/support/mockEgressTeardown.js',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: projects.length > 0 ? projects : [allProjects[0]],
  // Build once, then serve the static build for fast, production-like E2E.
  webServer: {
    command: `npm run build && npm run preview -- --config vite.mock-preview.config.js --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: BASE_URL,
    timeout: 180000,
    reuseExistingServer: false
  }
})
