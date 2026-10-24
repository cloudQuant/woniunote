let currentSession = null
let markerSequence = 0
let delayedRead = null

function makeMarker() {
  markerSequence += 1
  return `test-marker-${markerSequence}`
}

function copySession(session) {
  return {
    epoch: session.epoch,
    version: session.version,
    revision: Number.isSafeInteger(session.revision) ? session.revision : 0,
    token: session.token,
    refreshToken: session.refreshToken,
    user: session.user ? { ...session.user } : null
  }
}

function legacySession() {
  const canonical = globalThis.localStorage?.getItem('woniunote:auth-session')
  if (canonical) {
    try {
      const session = JSON.parse(canonical)
      if (session?.epoch && session?.version) return copySession(session)
    } catch {
      // Invalid test legacy mirrors are ignored like the production seeding path.
    }
  }

  let user = null
  try {
    user = JSON.parse(globalThis.localStorage?.getItem('user') || 'null')
  } catch {
    // The legacy user mirror is optional test fixture data.
  }
  return {
    epoch: globalThis.localStorage?.getItem('woniunote:auth-session-epoch') || makeMarker(),
    version: globalThis.localStorage?.getItem('woniunote:auth-session-version') || makeMarker(),
    token: globalThis.localStorage?.getItem('token') || '',
    refreshToken: globalThis.localStorage?.getItem('refreshToken') || '',
    user
  }
}

export const authSessionStorageMock = {
  reset() {
    currentSession = null
    markerSequence = 0
    delayedRead = null
  },
  setCurrent(session) {
    // Treat this helper as a committed remote write even when the test races
    // the first store read. Seed from the same legacy snapshot the adapter
    // would have selected, then allocate a new local mock revision.
    if (!currentSession) currentSession = copySession(legacySession())
    const requestedRevision = Number.isSafeInteger(session.revision) ? session.revision : -1
    const hasChanged = currentSession && (
      session.epoch !== currentSession.epoch || session.version !== currentSession.version ||
      session.token !== currentSession.token || session.refreshToken !== currentSession.refreshToken ||
      JSON.stringify(session.user ?? null) !== JSON.stringify(currentSession.user)
    )
    const nextRevision = Math.max(
      requestedRevision,
      currentSession ? currentSession.revision + (hasChanged ? 1 : 0) : 0
    )
    currentSession = copySession({ ...session, revision: nextRevision })
  },
  deferNextRead() {
    let startedResolve
    let releaseResolve
    const started = new Promise((resolve) => { startedResolve = resolve })
    const release = new Promise((resolve) => { releaseResolve = resolve })
    delayedRead = { startedResolve, release }
    return { started, release: () => releaseResolve() }
  },
  getCurrent() {
    return currentSession ? copySession(currentSession) : null
  },
  async readCurrent() {
    if (!currentSession) currentSession = copySession(legacySession())
    const snapshot = copySession(currentSession)
    if (delayedRead) {
      const gate = delayedRead
      delayedRead = null
      gate.startedResolve()
      await gate.release
    }
    return snapshot
  },
  async transact(update) {
    if (!currentSession) currentSession = copySession(legacySession())
    const current = copySession(currentSession)
    const decision = update(current)
    const committed = !!decision && Object.prototype.hasOwnProperty.call(decision, 'session')
    if (committed) currentSession = copySession({
      ...decision.session,
      revision: current.revision + 1
    })
    return {
      session: copySession(currentSession),
      result: decision?.result,
      committed
    }
  }
}
