import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// jsdom in some environments lacks a full localStorage; provide a stub so the
// store's persistence calls work deterministically under test.
const memoryStore = (() => {
  let data = {}
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v) },
    removeItem: (k) => { delete data[k] },
    clear: () => { data = {} }
  }
})()
vi.stubGlobal('localStorage', memoryStore)

vi.mock('@/utils/authSessionStorage', async () => {
  const { authSessionStorageMock } = await import('@/test/authSessionStorageMock')
  return { authSessionStorage: authSessionStorageMock }
})
import { authSessionStorageMock } from '@/test/authSessionStorageMock'

// Mock API + logger so the store works without network.
vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(() => Promise.resolve({
      data: {
        access_token: 'access-1',
        refresh_token: 'refresh-1',
        user: { userid: 1, nickname: 'tester', role: 'user' }
      }
    })),
    register: vi.fn(() => Promise.resolve({ data: { userid: 1 } })),
    getMe: vi.fn(() => Promise.resolve({ data: { userid: 1, nickname: 'tester', role: 'admin' } })),
    logout: vi.fn(() => Promise.resolve({ data: null }))
  }
}))

import { useUserStore } from './user'
import { authApi } from '@/api'

function stubWebLocks() {
  const ownDescriptor = Object.getOwnPropertyDescriptor(navigator, 'locks')
  const queue = []
  let held = false

  const grantNext = () => {
    if (held || queue.length === 0) return
    held = true
    const { callback, resolve, reject } = queue.shift()
    Promise.resolve()
      .then(callback)
      .then(resolve, reject)
      .finally(() => {
        held = false
        grantNext()
      })
  }

  const locks = {
    request: vi.fn((_name, callback) => new Promise((resolve, reject) => {
      queue.push({ callback, resolve, reject })
      grantNext()
    }))
  }
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: locks
  })

  return {
    locks,
    restore() {
      if (ownDescriptor) Object.defineProperty(navigator, 'locks', ownDescriptor)
      else delete navigator.locks
    }
  }
}

function storeSharedSession(session) {
  const current = authSessionStorageMock.getCurrent()
  authSessionStorageMock.setCurrent({
    ...session,
    revision: Math.max(session.revision ?? -1, (current?.revision ?? -1) + 1)
  })
  const durableSession = authSessionStorageMock.getCurrent()
  localStorage.setItem('woniunote:auth-session', JSON.stringify(durableSession))
  if (durableSession.token) localStorage.setItem('token', durableSession.token)
  else localStorage.removeItem('token')
  if (durableSession.refreshToken) localStorage.setItem('refreshToken', durableSession.refreshToken)
  else localStorage.removeItem('refreshToken')
  if (durableSession.user) localStorage.setItem('user', JSON.stringify(durableSession.user))
  else localStorage.removeItem('user')
}

describe('user store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    authSessionStorageMock.reset()
    vi.clearAllMocks()
  })

  it('starts logged out', () => {
    const store = useUserStore()
    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('loads the legacy keys when canonical storage is absent or invalid', async () => {
    localStorage.setItem('woniunote:auth-session', '{invalid')
    localStorage.setItem('woniunote:auth-session-epoch', 'legacy-epoch')
    localStorage.setItem('woniunote:auth-session-version', 'legacy-version')
    localStorage.setItem('token', 'legacy-token')
    localStorage.setItem('refreshToken', 'legacy-refresh')
    localStorage.setItem('user', '{invalid user')

    const store = useUserStore()
    await store.syncSession()
    expect(store.token).toBe('legacy-token')
    expect(store.refreshToken).toBe('legacy-refresh')
    expect(store.user).toBeNull()
  })

  it('creates session markers without crypto.randomUUID', async () => {
    const cryptoDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto')
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: undefined })
    try {
      const store = useUserStore()
      await store.login('tester', 'pw')
      expect(store.captureCredentials().epoch).toMatch(/^\d+-[a-z0-9]+$/)
    } finally {
      if (cryptoDescriptor) Object.defineProperty(globalThis, 'crypto', cryptoDescriptor)
      else delete globalThis.crypto
    }
  })

  it('tracks cross-tab storage only when the dispatched value is still current', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const priorGeneration = store.sessionGeneration
    const current = JSON.parse(localStorage.getItem('woniunote:auth-session'))
    const next = JSON.stringify({
      ...current,
      epoch: 'storage-event-epoch',
      version: 'storage-event-version',
      revision: current.revision + 1,
      token: 'storage-event-token',
      refreshToken: 'storage-event-refresh',
      user: { userid: 2, nickname: 'storage user' }
    })
    authSessionStorageMock.setCurrent(JSON.parse(next))
    localStorage.setItem('woniunote:auth-session', next)

    window.dispatchEvent(new StorageEvent('storage', {
      key: 'token',
      newValue: 'storage-event-token'
    }))
    expect(store.token).toBe('access-1')
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'woniunote:auth-session',
      newValue: JSON.stringify(current)
    }))
    await vi.waitFor(() => expect(store.token).toBe('storage-event-token'))

    authSessionStorageMock.setCurrent(JSON.parse(next))
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'woniunote:auth-session',
      newValue: next
    }))
    await store.syncSession()
    expect(store.token).toBe('storage-event-token')
    expect(store.user).toMatchObject({ userid: 2, nickname: 'storage user' })
    expect(store.sessionGeneration).toBeGreaterThan(priorGeneration)
  })

  it('ignores an IndexedDB read that completes after a newer login', async () => {
    const store = useUserStore()
    await store.login('first-user', 'pw')
    const staleRead = authSessionStorageMock.deferNextRead()
    const pendingSync = store.syncSession()
    await staleRead.started

    authApi.login.mockResolvedValueOnce({
      data: {
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        user: { userid: 2, nickname: 'new user', role: 'user' }
      }
    })
    await store.login('second-user', 'pw')
    const newerRevision = authSessionStorageMock.getCurrent().revision
    staleRead.release()
    await pendingSync

    expect(store.token).toBe('new-access')
    expect(store.user).toMatchObject({ userid: 2, nickname: 'new user' })
    expect(authSessionStorageMock.getCurrent()).toMatchObject({
      revision: newerRevision, token: 'new-access', user: { userid: 2 }
    })
  })

  it('does not resurrect an authenticated session when a stale read completes after logout', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const staleRead = authSessionStorageMock.deferNextRead()
    const pendingSync = store.syncSession()
    await staleRead.started

    await store.logout()
    const tombstone = authSessionStorageMock.getCurrent()
    staleRead.release()
    await pendingSync

    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(authSessionStorageMock.getCurrent()).toMatchObject({
      revision: tombstone.revision, token: '', refreshToken: '', user: null
    })
  })

  it('login stores tokens and user, persists to localStorage', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    expect(store.token).toBe('access-1')
    expect(store.refreshToken).toBe('refresh-1')
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('token')).toBe('access-1')
    expect(JSON.parse(localStorage.getItem('user')).nickname).toBe('tester')
  })

  it('keeps the committed session authoritative when legacy localStorage mirrors fail', async () => {
    const store = useUserStore()
    await store.syncSession()
    const mirrorWrite = vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })

    try {
      await store.login('tester', 'pw')
      expect(store).toMatchObject({ token: 'access-1', refreshToken: 'refresh-1', isLoggedIn: true })
      expect(authSessionStorageMock.getCurrent()).toMatchObject({
        token: 'access-1', refreshToken: 'refresh-1', user: { userid: 1 }
      })

      await store.syncSession()
      expect(store).toMatchObject({ token: 'access-1', refreshToken: 'refresh-1', isLoggedIn: true })
    } finally {
      mirrorWrite.mockRestore()
    }
  })

  it('fails closed and blocks future authentication when an authoritative session read fails', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const storageError = new Error('IndexedDB read failed')
    const readCurrent = vi.spyOn(authSessionStorageMock, 'readCurrent')
      .mockRejectedValueOnce(storageError)
    try {
      await expect(store.syncSession()).rejects.toBe(storageError)
      expect(store.token).toBe('')
      expect(store.refreshToken).toBe('')
      expect(store.user).toBeNull()
      expect(store.isLoggedIn).toBe(false)

      await expect(store.login('retry', 'pw')).rejects.toThrow('安全登录会话存储不可用')
      expect(authApi.login).toHaveBeenCalledOnce()
      expect(authApi.login).toHaveBeenCalledWith({ username: 'tester', password: 'pw' })
    } finally {
      readCurrent.mockRestore()
    }
  })

  it('keeps a newer login when an earlier login response arrives after it', async () => {
    let resolveSlowLogin
    authApi.login.mockImplementationOnce(() => new Promise((resolve) => {
      resolveSlowLogin = resolve
    }))
    const store = useUserStore()
    const slowLogin = store.login('slow-user', 'pw')
    await vi.waitFor(() => expect(resolveSlowLogin).toBeTypeOf('function'))

    authApi.login.mockResolvedValueOnce({
      data: {
        access_token: 'new-access', refresh_token: 'new-refresh',
        user: { userid: 2, username: 'new-user' }
      }
    })
    await store.login('new-user', 'pw')
    resolveSlowLogin({
      data: {
        access_token: 'slow-access', refresh_token: 'slow-refresh',
        user: { userid: 1, username: 'slow-user' }
      }
    })

    await expect(slowLogin).rejects.toThrow('登录状态已变化，请重新登录')
    expect(store).toMatchObject({ token: 'new-access', refreshToken: 'new-refresh' })
    expect(store.user).toMatchObject({ userid: 2, username: 'new-user' })
    expect(authSessionStorageMock.getCurrent()).toMatchObject({
      token: 'new-access', refreshToken: 'new-refresh', user: { userid: 2 }
    })
  })

  it('setTokens updates access token and optional refresh token', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    await store.setTokens('access-2')
    expect(store.token).toBe('access-2')
    // refresh token unchanged when not provided
    expect(store.refreshToken).toBe('refresh-1')
    await store.setTokens('access-3', 'refresh-3')
    expect(store.refreshToken).toBe('refresh-3')
    expect(localStorage.getItem('refreshToken')).toBe('refresh-3')
  })

  it('logout clears state and storage', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    await store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBe(null)
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBe(null)
    expect(authApi.logout).toHaveBeenCalledWith(expect.objectContaining({
      token: 'access-1', refreshToken: 'refresh-1', userId: 1
    }))
  })

  it('does not send a logout request when already logged out', async () => {
    const store = useUserStore()
    await expect(store.logout()).resolves.toMatchObject({ revoked: true })
    expect(authApi.logout).not.toHaveBeenCalled()
  })

  it('returns an unconfirmed revocation result when the API logout fails', async () => {
    authApi.logout.mockRejectedValueOnce(new Error('offline'))
    const store = useUserStore()
    await store.login('tester', 'pw')
    await expect(store.logout()).resolves.toMatchObject({
      revoked: false,
      error: expect.objectContaining({ message: 'offline' })
    })
    expect(store.token).toBe('')
  })

  it('reports unconfirmed logout when the durable local tombstone cannot commit', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const persistedBeforeLogout = authSessionStorageMock.getCurrent()
    const transactionError = new Error('IndexedDB write failed')
    const transact = vi.spyOn(authSessionStorageMock, 'transact')
      .mockRejectedValueOnce(transactionError)

    try {
      await expect(store.logout()).resolves.toMatchObject({
        revoked: false,
        error: transactionError
      })
      expect(store.token).toBe('')
      expect(store.refreshToken).toBe('')
      expect(store.user).toBeNull()
      expect(authApi.logout).toHaveBeenCalledWith(expect.objectContaining({
        token: persistedBeforeLogout.token,
        refreshToken: persistedBeforeLogout.refreshToken
      }))
      // The failed transaction must not be mistaken for a durable tombstone.
      expect(authSessionStorageMock.getCurrent()).toEqual(persistedBeforeLogout)
    } finally {
      transact.mockRestore()
    }
  })

  it('invalidates local state before waiting for remote logout confirmation', async () => {
    let resolveLogout
    authApi.logout.mockImplementationOnce(() => new Promise((resolve) => { resolveLogout = resolve }))
    const store = useUserStore()
    await store.login('tester', 'pw')

    const pendingLogout = store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBe(null)
    await vi.waitFor(() => expect(authApi.logout).toHaveBeenCalled())
    expect(authApi.logout).toHaveBeenCalledWith(expect.objectContaining({ token: 'access-1' }))
    resolveLogout({ data: null })
    await expect(pendingLogout).resolves.toMatchObject({ revoked: true })
  })

  it('logout clears a same-epoch token rotation completed by the lock holder first', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const captured = store.captureCredentials()
    const shared = JSON.parse(localStorage.getItem('woniunote:auth-session'))
    const { locks, restore } = stubWebLocks()
    let releaseRefresh
    let signalRefresh
    const refreshHeldLock = new Promise((resolve) => { signalRefresh = resolve })
    const refreshLock = locks.request('woniunote:auth-session-lock', async () => {
      signalRefresh()
      await new Promise((resolve) => { releaseRefresh = resolve })
      storeSharedSession({
        ...shared,
        version: 'rotated-version',
        token: 'rotated-access',
        refreshToken: 'rotated-refresh'
      })
    })

    try {
      await refreshHeldLock
      const pendingLogout = store.logout()
      expect(store.sessionGeneration).toBeGreaterThan(captured.generation)
      releaseRefresh()
      await Promise.all([refreshLock, pendingLogout])

      expect(store.token).toBe('')
      expect(store.refreshToken).toBe('')
      expect(JSON.parse(localStorage.getItem('woniunote:auth-session')).token).toBe('')
      expect(authApi.logout).toHaveBeenCalledWith(expect.objectContaining({
        token: captured.token,
        refreshToken: captured.refreshToken
      }))
    } finally {
      restore()
    }
  })

  it('logout preserves a different epoch that wins the shared lock first', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const captured = store.captureCredentials()
    const shared = JSON.parse(localStorage.getItem('woniunote:auth-session'))
    const { locks, restore } = stubWebLocks()
    let releaseLogin
    let signalLogin
    const loginHeldLock = new Promise((resolve) => { signalLogin = resolve })
    const loginLock = locks.request('woniunote:auth-session-lock', async () => {
      signalLogin()
      await new Promise((resolve) => { releaseLogin = resolve })
      storeSharedSession({
        ...shared,
        epoch: 'new-login-epoch',
        version: 'new-login-version',
        token: 'new-login-access',
        refreshToken: 'new-login-refresh',
        user: { userid: 2, nickname: 'new account' }
      })
    })

    try {
      await loginHeldLock
      const pendingLogout = store.logout()
      releaseLogin()
      await Promise.all([loginLock, pendingLogout])

      expect(store.token).toBe('new-login-access')
      expect(store.user).toMatchObject({ userid: 2, nickname: 'new account' })
      expect(JSON.parse(localStorage.getItem('woniunote:auth-session')).epoch).toBe('new-login-epoch')
      expect(authApi.logout).toHaveBeenCalledWith(expect.objectContaining({ token: captured.token }))
    } finally {
      restore()
    }
  })

  it('logout queued before a refresh fences its stale token update', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const captured = store.captureCredentials()
    const { locks, restore } = stubWebLocks()
    let releaseBlocker
    let signalBlocker
    const blockerHeldLock = new Promise((resolve) => { signalBlocker = resolve })
    const blocker = locks.request('woniunote:auth-session-lock', async () => {
      signalBlocker()
      await new Promise((resolve) => { releaseBlocker = resolve })
    })

    try {
      await blockerHeldLock
      const pendingLogout = store.logout()
      const pendingRefresh = store.setTokens('late-access', 'late-refresh', captured)
      releaseBlocker()
      await Promise.all([blocker, pendingLogout, pendingRefresh])

      expect(store.token).toBe('')
      expect(JSON.parse(localStorage.getItem('woniunote:auth-session')).token).toBe('')
    } finally {
      restore()
    }
  })

  it('does not overwrite a newer durable cross-tab identity with a late refresh result', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const savedState = JSON.parse(localStorage.getItem('woniunote:auth-session') || 'null') || {
      epoch: 'legacy-epoch', version: 'legacy-version'
    }
    const snapshot = {
      generation: store.sessionGeneration,
      epoch: savedState.epoch,
      token: store.token,
      refreshToken: store.refreshToken,
      userIdentity: 'id:1'
    }
    const newer = {
      ...savedState,
      epoch: 'new-tab-login',
      version: 'new-tab-version',
      token: 'new-tab-access',
      refreshToken: 'new-tab-refresh',
      user: { userid: 2, nickname: 'new identity', role: 'user' }
    }
    storeSharedSession(newer)

    await Promise.resolve(store.setTokens('late-access', 'late-refresh', snapshot))
    expect(store.token).toBe('new-tab-access')
    expect(store.user.userid).toBe(2)
    expect(JSON.parse(localStorage.getItem('woniunote:auth-session')).token).toBe('new-tab-access')
  })

  it('rejects a late same-session token rotation after newer credentials commit', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw')
    const oldCredentials = store.captureCredentials()

    await store.setTokens('rotated-access', 'rotated-refresh')
    await expect(store.setTokens('late-access', 'late-refresh', oldCredentials)).resolves.toBe(false)

    expect(store.token).toBe('rotated-access')
    expect(store.refreshToken).toBe('rotated-refresh')
    expect(store.isSessionCurrent(oldCredentials)).toBe(true)
    expect(store.isCredentialsCurrent(oldCredentials)).toBe(false)
    expect(authSessionStorageMock.getCurrent()).toMatchObject({
      epoch: oldCredentials.epoch,
      token: 'rotated-access',
      refreshToken: 'rotated-refresh'
    })
  })

  it('ignores a late getMe response after a newer login', async () => {
    let resolveMe
    authApi.getMe.mockImplementationOnce(() => new Promise((resolve) => { resolveMe = resolve }))
    const store = useUserStore()
    await store.login('tester', 'pw')
    const pendingMe = store.refreshUserInfo()
    await Promise.resolve()
    authApi.login.mockResolvedValueOnce({
      data: { access_token: 'access-2', refresh_token: 'refresh-2', user: { userid: 2, nickname: 'new user' } }
    })
    await store.login('new-user', 'pw')
    resolveMe({ data: { userid: 1, nickname: 'stale user', role: 'admin' } })
    await pendingMe

    expect(store.token).toBe('access-2')
    expect(store.user).toMatchObject({ userid: 2, nickname: 'new user' })
  })

  it('ignores a late getMe response after durable storage changes before its event', async () => {
    let resolveMe
    authApi.getMe.mockImplementationOnce(() => new Promise((resolve) => { resolveMe = resolve }))
    const store = useUserStore()
    await store.login('tester', 'pw')
    const pendingMe = store.refreshUserInfo()
    await vi.waitFor(() => expect(authApi.getMe).toHaveBeenCalledOnce())

    const current = JSON.parse(localStorage.getItem('woniunote:auth-session'))
    const newerSession = {
      ...current,
      epoch: 'new-tab-login',
      version: 'new-tab-version',
      token: 'new-tab-access',
      refreshToken: 'new-tab-refresh',
      user: { userid: 2, nickname: 'new identity', role: 'user' }
    }
    storeSharedSession(newerSession)
    resolveMe({ data: { userid: 1, nickname: 'stale admin', role: 'admin' } })
    await pendingMe

    expect(store.token).toBe('new-tab-access')
    expect(store.user).toMatchObject({ userid: 2, nickname: 'new identity', role: 'user' })
    expect(JSON.parse(localStorage.getItem('woniunote:auth-session'))).toMatchObject({
      epoch: newerSession.epoch,
      version: newerSession.version,
      token: newerSession.token,
      refreshToken: newerSession.refreshToken,
      user: newerSession.user
    })
  })

  it('does not clear a newer identity when the older getMe request fails late', async () => {
    let rejectMe
    authApi.getMe.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectMe = reject }))
    const store = useUserStore()
    await store.login('tester', 'pw')
    const pendingMe = store.refreshUserInfo()
    await vi.waitFor(() => expect(rejectMe).toBeTypeOf('function'))

    const current = JSON.parse(localStorage.getItem('woniunote:auth-session'))
    const newer = {
      ...current,
      epoch: 'failed-me-new-epoch',
      version: 'failed-me-new-version',
      token: 'new-token',
      refreshToken: 'new-refresh',
      user: { userid: 2, nickname: 'new identity' }
    }
    storeSharedSession(newer)
    rejectMe(new Error('late 401'))
    await pendingMe

    expect(store.token).toBe('new-token')
    expect(store.user).toMatchObject({ userid: 2, nickname: 'new identity' })
  })

  it('tracks identities and editor owners by id and username fallbacks', async () => {
    const store = useUserStore()
    authApi.login.mockResolvedValueOnce({
      data: { access_token: 'id-token', refresh_token: 'id-refresh', user: { id: 2 } }
    })
    await store.login('id-user', 'pw')
    expect(store.captureCredentials()).toMatchObject({ userIdentity: 'id:2', userId: 2 })

    authApi.login.mockResolvedValueOnce({
      data: { access_token: 'name-token', refresh_token: 'name-refresh', user: { username: 'named' } }
    })
    await store.login('named', 'pw')
    expect(store.captureCredentials()).toMatchObject({ userIdentity: 'name:named', userId: 'named' })
  })

  it('isAdmin reflects role', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    expect(store.isAdmin).toBe(false)
    await store.refreshUserInfo()
    expect(store.isAdmin).toBe(true)
  })
})
