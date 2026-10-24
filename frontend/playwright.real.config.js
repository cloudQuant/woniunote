import { chmodSync, mkdirSync } from 'node:fs'
import path from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const runId = process.env.WONIUNOTE_TEST_RUN_ID || ''
const realE2e = process.env.WONIUNOTE_REAL_E2E === '1'
const frontendUrl = process.env.WONIUNOTE_REAL_E2E_URL || ''
const backendTarget = process.env.WONIUNOTE_API_PROXY_TARGET || ''
const evidenceDir = process.env.WONIUNOTE_TEST_EVIDENCE_DIR || ''

if (!realE2e || !/^\d{8}T\d{6}Z-[0-9a-f]{12}$/.test(runId)) {
  throw new Error('Real E2E is only available from the isolated Iteration 21 runner')
}
if (!evidenceDir || !path.isAbsolute(evidenceDir)) {
  throw new Error('Real E2E requires an absolute per-run evidence directory')
}
const origin = new URL(frontendUrl)
if (origin.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(origin.hostname) ||
    !origin.port || [5173, 8888, 3306, 6379].includes(Number(origin.port))) {
  throw new Error('Real E2E frontend URL must use an owned loopback port')
}
const backend = new URL(backendTarget)
if (backend.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]', '::1'].includes(backend.hostname) ||
    !backend.port || [5173, 8888, 3306, 6379].includes(Number(backend.port))) {
  throw new Error('Real E2E backend target must use an owned loopback port')
}

const runEvidenceDir = path.join(evidenceDir, `playwright-${runId}`)
mkdirSync(runEvidenceDir, { recursive: true, mode: 0o700 })
chmodSync(runEvidenceDir, 0o700)
const outputDir = path.join(runEvidenceDir, 'test-results')
const reportDir = path.join(runEvidenceDir, 'html-report')

export default defineConfig({
  testDir: './e2e-real',
  testMatch: '**/*.spec.js',
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  outputDir,
  reporter: [
    ['list'],
    ['html', { outputFolder: reportDir, open: 'never' }]
  ],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: frontendUrl,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
    actionTimeout: 15000,
    navigationTimeout: 30000
  },
  projects: [{ name: 'chromium-real', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${origin.port} --strictPort`,
    url: frontendUrl,
    timeout: 180000,
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe'
  }
})
