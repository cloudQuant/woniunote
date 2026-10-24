import { randomUUID } from 'node:crypto'
import { mkdirSync, readFileSync, readdirSync, renameSync, writeFileSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'

const MAX_AUDIT_EVENTS = 24
const contextAudits = new WeakMap()

function apiOrUploadPath(requestUrl) {
  let pathname
  try {
    pathname = new URL(requestUrl).pathname
  } catch {
    return null
  }
  return pathname === '/api' || pathname.startsWith('/api/') ||
    pathname === '/uploads' || pathname.startsWith('/uploads/')
    ? pathname
    : null
}

function safeMethod(method) {
  const cleaned = String(method || 'UNKNOWN').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 12)
  return cleaned || 'UNKNOWN'
}

function safePath(pathname) {
  const characters = Array.from(pathname, (character) => {
    const code = character.codePointAt(0)
    return code <= 31 || code === 127 ? '?' : character
  })
  return characters.join('').slice(0, 240)
}

function normalizeTestInfo(testInfo) {
  if (!testInfo || typeof testInfo !== 'object') return null
  const testId = String(testInfo.testId || '').slice(0, 160)
  const project = String(testInfo.project || '').slice(0, 80)
  const file = basename(String(testInfo.file || '').replaceAll('\\', '/')).slice(0, 120)
  const line = Number.isSafeInteger(testInfo.line) && testInfo.line > 0 ? testInfo.line : null
  if (!testId || !project || !file || line === null) return null
  return { testId, project, file, line }
}

function hasTestInfo(testInfo) {
  return Boolean(testInfo && typeof testInfo.testId === 'string' && testInfo.testId &&
    typeof testInfo.project === 'string' && testInfo.project &&
    typeof testInfo.file === 'string' && testInfo.file &&
    Number.isSafeInteger(testInfo.line) && testInfo.line > 0)
}

function describeContextTest(context) {
  const testInfo = context.testInfo
  if (!hasTestInfo(testInfo)) return 'unattributed test'
  return `${testInfo.project}/${testInfo.file}:${testInfo.line} [${testInfo.testId}]`
}

function atomicWrite(filePath, value) {
  const temporaryPath = filePath + '.' + process.pid + '.tmp'
  writeFileSync(temporaryPath, JSON.stringify(value), { encoding: 'utf8', mode: 0o600 })
  renameSync(temporaryPath, filePath)
}

export function createMockEgressLog(logPath) {
  if (!logPath) throw new Error('Mock E2E preview requires WONIUNOTE_MOCK_EGRESS_LOG')
  mkdirSync(dirname(logPath), { recursive: true })
  writeMockEgressState(logPath, {
    schemaVersion: 1,
    ready: true,
    deniedCount: 0,
    events: [],
    eventsTruncated: false
  })
}

export function writeMockEgressState(logPath, state) {
  atomicWrite(logPath, state)
}

export function recordMockEgressDenied(logPath, state, method, pathname) {
  state.deniedCount += 1
  if (state.events.length < MAX_AUDIT_EVENTS) {
    state.events.push({ method: safeMethod(method), path: safePath(pathname) })
  } else {
    state.eventsTruncated = true
  }
  writeMockEgressState(logPath, state)
}

export function readMockEgressLog(logPath) {
  if (!logPath) throw new Error('Mock E2E did not configure an egress audit path')
  let state
  try {
    state = JSON.parse(readFileSync(logPath, 'utf8'))
  } catch (error) {
    throw new Error('Mock E2E egress audit is missing or unreadable: ' + logPath, { cause: error })
  }
  if (state?.schemaVersion !== 1 || state.ready !== true ||
      !Number.isSafeInteger(state.deniedCount) || state.deniedCount < 0 ||
      !Array.isArray(state.events) || typeof state.eventsTruncated !== 'boolean') {
    throw new Error('Mock E2E egress audit has an invalid or incomplete record')
  }
  return state
}

export function readMockContextAudits(logPath) {
  if (!logPath) throw new Error('Mock E2E did not configure a context audit path')
  const directory = dirname(logPath)
  const prefix = basename(logPath) + '.context.'
  let fileNames
  try {
    fileNames = readdirSync(directory).filter((fileName) => fileName.startsWith(prefix))
  } catch (error) {
    throw new Error('Mock E2E context audit directory is missing or unreadable: ' + directory, { cause: error })
  }
  return fileNames.map((fileName) => {
    let state
    try {
      state = JSON.parse(readFileSync(join(directory, fileName), 'utf8'))
    } catch (error) {
      throw new Error('Mock E2E context audit is unreadable: ' + fileName, { cause: error })
    }
    if (state?.schemaVersion !== 1 || state.ready !== true ||
        typeof state.closed !== 'boolean' ||
        !Number.isSafeInteger(state.violationCount) || state.violationCount < 0 ||
        !Array.isArray(state.events) || typeof state.eventsTruncated !== 'boolean') {
      throw new Error('Mock E2E context audit is invalid or incomplete: ' + fileName)
    }
    return state
  })
}

export function assertNoMockEgress(logPath, { requireContexts = true } = {}) {
  if (typeof requireContexts !== 'boolean') {
    throw new TypeError('Mock E2E requireContexts must be a boolean')
  }
  const egress = readMockEgressLog(logPath)
  const contexts = readMockContextAudits(logPath)
  const unclosedContexts = contexts.filter((context) => context.closed !== true)
  const violatedContexts = contexts.filter((context) => context.violationCount !== 0)
  const unattributedContexts = contexts.filter((context) => !hasTestInfo(context.testInfo))
  const failures = []
  if (requireContexts && contexts.length === 0) {
    failures.push('Mock E2E has no browser context audit records')
  }
  if (requireContexts && unattributedContexts.length) {
    failures.push(unattributedContexts.length + ' mock context audit(s) have no valid test attribution')
  }
  if (egress.deniedCount !== 0) {
    const examples = egress.events.map(({ method, path }) => method + ' ' + path).join(', ')
    const suffix = egress.eventsTruncated ? ' (additional events omitted)' : ''
    failures.push('Mock preview denied ' + egress.deniedCount + ' API/upload request(s): ' + examples + suffix)
  }
  if (unclosedContexts.length) failures.push(unclosedContexts.length + ' mock context audit(s) remained open')
  if (violatedContexts.length) {
    const examples = violatedContexts.flatMap((context) => context.events.map(({ kind, method, path, reason }) =>
      describeContextTest(context) + ': ' + kind + ' ' + method + ' ' + path + (reason ? ' (' + reason + ')' : '')))
      .slice(0, MAX_AUDIT_EVENTS)
      .join('; ')
    failures.push(violatedContexts.length + ' mock context audit(s) recorded violations: ' + examples)
  }
  if (failures.length) throw new Error(failures.join(' | '))
  return egress
}

export function watchMockContext(context, testInfo = null) {
  const existing = contextAudits.get(context)
  if (existing) {
    existing.setTestInfo(testInfo)
    return existing
  }

  const logPath = process.env.WONIUNOTE_MOCK_EGRESS_LOG
  if (!logPath) throw new Error('Mock E2E context requires WONIUNOTE_MOCK_EGRESS_LOG')
  const auditPath = logPath + '.context.' + process.pid + '-' + randomUUID()
  const state = {
    phase: 'active',
    events: [],
    violationCount: 0,
    eventsTruncated: false,
    activeRequests: new Map(),
    pages: new Set(),
    closed: false,
    testInfo: normalizeTestInfo(testInfo)
  }
  const persist = () => atomicWrite(auditPath, {
    schemaVersion: 1,
    ready: true,
    closed: state.closed,
    testInfo: state.testInfo,
    violationCount: state.violationCount,
    events: state.events,
    eventsTruncated: state.eventsTruncated
  })
  const addEvent = (event, violation = true) => {
    const safeEvent = {
      kind: event.kind,
      method: safeMethod(event.method),
      path: safePath(event.path),
      phase: state.phase,
      reason: event.reason || ''
    }
    if (state.events.length < MAX_AUDIT_EVENTS) state.events.push(safeEvent)
    else state.eventsTruncated = true
    if (violation) state.violationCount += 1
    persist()
  }

  context.on('page', (page) => state.pages.add(page))
  for (const page of context.pages()) state.pages.add(page)
  context.on('request', (request) => {
    const pathname = apiOrUploadPath(request.url())
    if (pathname) state.activeRequests.set(request, { method: request.method(), path: pathname })
  })
  context.on('requestfinished', (request) => state.activeRequests.delete(request))
  context.on('response', (response) => {
    const request = response.request()
    const pathname = apiOrUploadPath(request.url())
    if (!pathname) return
    if (response.headers()['x-woniunote-mock-egress'] === 'blocked') {
      addEvent({ kind: 'preview-egress-denied', method: request.method(), path: pathname })
    }
  })
  context.on('requestfailed', (request) => {
    const pathname = apiOrUploadPath(request.url())
    if (!pathname) return
    state.activeRequests.delete(request)
    const failure = request.failure()?.errorText || ''
    const knownAbort = ['ERR_ABORTED', 'ERR_CANCELED', 'NS_BINDING_ABORTED']
      .find((reason) => failure.includes(reason))
    const isWrite = !['GET', 'HEAD', 'OPTIONS'].includes(request.method().toUpperCase())
    const teardownReadCancelled = state.phase === 'teardown' && !isWrite && Boolean(knownAbort)
    addEvent({
      kind: teardownReadCancelled ? 'teardown-read-cancelled' : 'unconfirmed-api-request',
      method: request.method(),
      path: pathname,
      reason: knownAbort || (failure ? 'NETWORK_FAILURE' : '')
    }, !teardownReadCancelled)
  })
  context.on('close', () => {
    for (const { method, path } of state.activeRequests.values()) {
      addEvent({ kind: 'unconfirmed-api-at-context-close', method, path })
    }
    state.activeRequests.clear()
    state.closed = true
    persist()
  })
  persist()

  const audit = {
    pages: state.pages,
    setTestInfo(metadata) {
      const normalized = normalizeTestInfo(metadata)
      if (!normalized) return
      if (state.testInfo && state.testInfo.testId !== normalized.testId) {
        addEvent({ kind: 'context-test-attribution-conflict', method: 'UNKNOWN', path: '/mock-context' })
        return
      }
      state.testInfo = normalized
      persist()
    },
    recordUnexpected(method, pathname) {
      addEvent({ kind: 'unmatched-mock-api', method, path: pathname })
    },
    beginTeardown() {
      state.phase = 'teardown'
    },
    assertClean() {
      for (const { method, path } of state.activeRequests.values()) {
        addEvent({ kind: 'unconfirmed-api-at-test-end', method, path })
      }
      if (state.violationCount) {
        const details = state.events.map(({ kind, method, path, reason }) =>
          kind + ' ' + method + ' ' + path + (reason ? ' (' + reason + ')' : '')).join('; ')
        throw new Error('Mock E2E context observed unconfirmed API activity: ' + details)
      }
    }
  }
  contextAudits.set(context, audit)
  return audit
}

export function recordUnexpectedMockApi(page, method, pathname) {
  watchMockContext(page.context()).recordUnexpected(method, pathname)
}

export function getMockContextPages(context) {
  return [...(contextAudits.get(context)?.pages || []), ...context.pages()]
}
