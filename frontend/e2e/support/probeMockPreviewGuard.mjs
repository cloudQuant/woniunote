import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { randomUUID } from 'node:crypto'
import process from 'node:process'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { preview } from 'vite'
import { assertNoMockEgress, createMockEgressLog, readMockEgressLog } from './mockEgress.js'

delete process.env.E2E_BASE_URL
delete process.env.WONIUNOTE_REAL_E2E
delete process.env.WONIUNOTE_API_PROXY_TARGET

const egressLogPath = join(tmpdir(), 'woniunote-mock-guard-probe-' + process.pid + '-' + randomUUID() + '.json')
process.env.WONIUNOTE_MOCK_EGRESS_LOG = egressLogPath
let sentinelHits = 0
const sentinel = createServer((request, response) => {
  sentinelHits += 1
  response.statusCode = 200
  response.end('sentinel reached')
})
let previewServer

try {
  await new Promise((resolveListen, reject) => {
    sentinel.once('error', reject)
    sentinel.listen(5173, '127.0.0.1', resolveListen)
  })
  previewServer = await preview({
    configFile: resolve('vite.mock-preview.config.js'),
    preview: { host: '127.0.0.1', port: 0, strictPort: false }
  })
  const address = previewServer.httpServer.address()
  assert.ok(address && typeof address === 'object')
  const origin = 'http://127.0.0.1:' + address.port

  for (const path of ['/api/__guard_probe', '/uploads/__guard_probe']) {
    for (const method of ['GET', 'POST']) {
      const response = await fetch(origin + path, { method })
      assert.equal(response.status, 503, method + ' ' + path + ' must be denied by the mock preview')
      assert.equal(response.headers.get('x-woniunote-mock-egress'), 'blocked')
      await response.arrayBuffer()
    }
  }

  assert.equal(sentinelHits, 0, 'the API proxy sentinel on port 5173 must not receive requests')
  const audit = readMockEgressLog(egressLogPath)
  assert.equal(audit.deniedCount, 4)
  assert.deepEqual(audit.events.map(({ method, path }) => method + ' ' + path), [
    'GET /api/__guard_probe',
    'POST /api/__guard_probe',
    'GET /uploads/__guard_probe',
    'POST /uploads/__guard_probe'
  ])

  let gateError
  try {
    // This probe intentionally has no browser context: it verifies only the
    // preview server boundary and opts out of the formal browser-context gate.
    assertNoMockEgress(egressLogPath, { requireContexts: false })
  } catch (error) {
    gateError = error
  }
  assert.match(gateError?.message || '', /Mock preview denied 4 API\/upload request/)

  assert.throws(
    () => assertNoMockEgress(egressLogPath + '.missing-server-record', { requireContexts: false }),
    /audit is missing or unreadable/
  )
  const emptyContextAuditPath = egressLogPath + '.empty-context'
  createMockEgressLog(emptyContextAuditPath)
  assert.throws(
    () => assertNoMockEgress(emptyContextAuditPath),
    /no browser context audit records/
  )
  assert.doesNotThrow(() => assertNoMockEgress(emptyContextAuditPath, { requireContexts: false }))
  process.stdout.write('Mock preview guard probe passed; expected global gate rejection recorded at ' + egressLogPath + '\n')
} finally {
  await previewServer?.close()
  await new Promise((resolveClose) => sentinel.close(resolveClose))
}
