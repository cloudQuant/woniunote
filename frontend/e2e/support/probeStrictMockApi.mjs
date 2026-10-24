import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import process from 'node:process'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { chromium } from 'playwright'
import { preview } from 'vite'
import { assertNoMockEgress, watchMockContext } from './mockEgress.js'
import { assertNoUnexpectedApiRequests, getUnexpectedApiRequests, mockApi } from './mockApi.js'

delete process.env.E2E_BASE_URL
delete process.env.WONIUNOTE_REAL_E2E
delete process.env.WONIUNOTE_API_PROXY_TARGET

const egressLogPath = join(tmpdir(), 'woniunote-strict-mock-probe-' + process.pid + '-' + randomUUID() + '.json')
process.env.WONIUNOTE_MOCK_EGRESS_LOG = egressLogPath
let previewServer
let browser
let context

try {
  previewServer = await preview({
    configFile: resolve('vite.mock-preview.config.js'),
    preview: { host: '127.0.0.1', port: 0, strictPort: false }
  })
  const address = previewServer.httpServer.address()
  assert.ok(address && typeof address === 'object')
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {})
  })
  context = await browser.newContext()
  watchMockContext(context, {
    testId: 'strict-mock-api-probe',
    project: 'probe',
    file: 'probeStrictMockApi.mjs',
    line: 1
  })
  const page = await context.newPage()
  await mockApi(page)
  await page.goto('http://127.0.0.1:' + address.port + '/')
  const response = await page.evaluate(async () => {
    const result = await fetch('/api/__strict_mock_gate_probe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ probe: true })
    })
    return { status: result.status, body: await result.json() }
  })

  assert.equal(response.status, 501)
  assert.match(response.body.message, /POST \/api\/__strict_mock_gate_probe/)
  assert.equal(getUnexpectedApiRequests(page).length, 1)
  assert.throws(
    () => assertNoUnexpectedApiRequests(page),
    /POST \/api\/__strict_mock_gate_probe/
  )

  await context.close()
  context = null
  let globalGateError
  try {
    assertNoMockEgress(egressLogPath)
  } catch (error) {
    globalGateError = error
  }
  assert.match(globalGateError?.message || '', /unmatched-mock-api POST \/api\/__strict_mock_gate_probe/)
  process.stdout.write('Strict mock probe passed: unknown API path was recorded and both strict gates rejected it.\n')
} finally {
  if (context) await context.close()
  await browser?.close()
  await previewServer?.close()
}
