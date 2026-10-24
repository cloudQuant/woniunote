import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Tests for the axios instance interceptors in src/api/index.js.
 *
 * Strategy: axios.create returns a fake instance whose interceptor `use`
 * callbacks we capture, then invoke directly to exercise request/response/error
 * handling (token injection, 401 silent refresh, error mapping) without a real
 * network or a real axios.
 */

// ---- Captured interceptor handlers (populated when the module registers them) ----
const handlers = vi.hoisted(() => ({
  requestFulfilled: null,
  requestRejected: null,
  responseFulfilled: null,
  responseRejected: null
}))

// Shared mock state is created via vi.hoisted so it exists before the hoisted
// vi.mock factories AND the hoisted ES imports run.
const h = vi.hoisted(() => {
  const postMock = vi.fn() // bare axios.post used by refreshAccessToken
  // The api instance is callable (api(config)) AND has .get/.post/etc.
  const apiInstance = vi.fn(() => Promise.resolve({ replayed: true }))
  apiInstance.get = vi.fn()
  apiInstance.post = vi.fn()
  apiInstance.put = vi.fn()
  apiInstance.delete = vi.fn()
  return { postMock, apiInstance }
})
const postMock = h.postMock
const apiInstance = h.apiInstance

vi.mock('axios', () => {
  const create = vi.fn(() => {
    // Attach interceptors here so they're present when index.js registers them
    // (ES imports are hoisted above top-level test statements).
    h.apiInstance.interceptors = {
      request: {
        use: (f, r) => { handlers.requestFulfilled = f; handlers.requestRejected = r }
      },
      response: {
        use: (f, r) => { handlers.responseFulfilled = f; handlers.responseRejected = r }
      }
    }
    return h.apiInstance
  })
  return {
    default: { create, post: (...a) => h.postMock(...a) },
    create,
    post: (...a) => h.postMock(...a)
  }
})

// Epic 18.1: the response interceptor must NOT toast HTTP/business errors any
// more — views own user-facing feedback via notifyError. Keep a callable spy
// (ElMessage({...}) + ElMessage.error(...)) so the specs can guard the absence.
const elMessage = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: Object.assign((...a) => elMessage(...a), {
    error: (...a) => elMessage(...a),
    warning: (...a) => elMessage(...a)
  })
}))

const routerPush = vi.fn()
const routerCurrentRoute = vi.hoisted(() => ({ value: { fullPath: '/' } }))
vi.mock('@/router', () => ({
  default: { push: (...a) => routerPush(...a), currentRoute: routerCurrentRoute }
}))

const apiTestStorage = (() => {
  let data = {}
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => { data[key] = String(value) },
    removeItem: (key) => { delete data[key] },
    clear: () => { data = {} }
  }
})()
vi.stubGlobal('localStorage', apiTestStorage)
let durableSessionEnabled = false

const userStore = {
  token: '',
  refreshToken: '',
  user: { userid: 1 },
  sessionGeneration: 1,
  epoch: 'epoch-1',
  version: 'version-1',
  syncSession: vi.fn(async () => {
    userStore.syncDurableSession()
    return userStore.captureCredentials()
  }),
  syncDurableSession() {
    if (!durableSessionEnabled) return
    const raw = localStorage.getItem('woniunote:auth-session')
    if (!raw) return
    const shared = JSON.parse(raw)
    if (shared.version === userStore.version && shared.epoch === userStore.epoch) return
    if (shared.epoch !== userStore.epoch) userStore.sessionGeneration += 1
    userStore.epoch = shared.epoch
    userStore.version = shared.version
    userStore.token = shared.token
    userStore.refreshToken = shared.refreshToken
    userStore.user = shared.user
  },
  captureCredentials: vi.fn(() => ({
    ...userStore.syncDurableSession(),
    generation: userStore.sessionGeneration,
    epoch: userStore.epoch,
    version: userStore.version,
    token: userStore.token,
    refreshToken: userStore.refreshToken,
    userIdentity: userStore.user?.userid ? `id:${userStore.user.userid}` : null,
    userId: userStore.user?.userid ?? null
  })),
  isSessionCurrent: vi.fn((snapshot) => {
    userStore.syncDurableSession()
    return snapshot?.generation === userStore.sessionGeneration &&
    snapshot?.epoch === userStore.epoch &&
    snapshot?.userIdentity === (userStore.user?.userid ? `id:${userStore.user.userid}` : null)
  }),
  isCredentialsCurrent: vi.fn((snapshot) => userStore.isSessionCurrent(snapshot) &&
    snapshot.token === userStore.token && snapshot.refreshToken === userStore.refreshToken),
  setTokens: vi.fn(async (accessToken, refreshToken, snapshot) => {
    if (snapshot && !userStore.isCredentialsCurrent(snapshot)) return false
    userStore.token = accessToken
    if (refreshToken) userStore.refreshToken = refreshToken
    userStore.version = `version-${Date.now()}`
    return true
  }),
  clearSession: vi.fn(async (snapshot) => {
    if (snapshot && !userStore.isCredentialsCurrent(snapshot)) return false
    userStore.token = ''
    userStore.refreshToken = ''
    userStore.user = null
    userStore.epoch = `epoch-${Date.now()}`
    userStore.sessionGeneration += 1
    return true
  }),
  logout: vi.fn()
}
vi.mock('@/stores/user', () => ({
  useUserStore: () => userStore
}))

vi.mock('@/utils/logger', () => ({
  logInfo: vi.fn(),
  logError: vi.fn(),
  logWarning: vi.fn(),
  logRequest: vi.fn()
}))

const startLoading = vi.fn()
const stopLoading = vi.fn()
vi.mock('@/utils/loading', () => ({
  startLoading: (...a) => startLoading(...a),
  stopLoading: (...a) => stopLoading(...a)
}))

function installNavigatorLocks(request) {
  const descriptor = Object.getOwnPropertyDescriptor(navigator, 'locks')
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: { request }
  })
  return () => {
    if (descriptor) Object.defineProperty(navigator, 'locks', descriptor)
    else delete navigator.locks
  }
}

// Import after mocks so interceptors register against the fake instance.
import { logWarning } from '@/utils/logger'
import { registerEditorSnapshotProvider } from '@/utils/editorRecovery'
import apiDefault, {
  authApi,
  articleApi,
  commentApi,
  favoriteApi,
  userApi,
  uploadApi,
  creditApi,
  adminApi,
  myCommentApi,
  draftApi,
  systemApi,
  mathTrainingApi
} from './index'

describe('api interceptors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    userStore.token = ''
    Object.defineProperty(userStore, 'refreshToken', { configurable: true, enumerable: true, writable: true, value: '' })
    userStore.user = { userid: 1 }
    userStore.sessionGeneration = 1
    userStore.epoch = 'epoch-1'
    userStore.version = 'version-1'
    routerCurrentRoute.value = { fullPath: '/' }
    durableSessionEnabled = false
    localStorage.clear()
  })

  describe('request interceptor', () => {
    it('starts loading and injects Authorization when token present', async () => {
      userStore.token = 'abc'
      const cfg = await handlers.requestFulfilled({ method: 'get', url: '/x', headers: {} })
      expect(startLoading).toHaveBeenCalledOnce()
      expect(cfg._loadingStarted).toBe(true)
      expect(cfg.headers.Authorization).toBe('Bearer abc')
      expect(cfg.metadata.startTime).toBeTypeOf('number')
    })

    it('skips loading when config.skipLoading is set', async () => {
      const cfg = await handlers.requestFulfilled({ method: 'get', url: '/x', headers: {}, skipLoading: true })
      expect(startLoading).not.toHaveBeenCalled()
      expect(cfg._loadingStarted).toBeUndefined()
    })

    it('omits Authorization when no token', async () => {
      const cfg = await handlers.requestFulfilled({ method: 'get', url: '/x', headers: {} })
      expect(cfg.headers.Authorization).toBeUndefined()
    })

    it('injects the captured bearer token for an explicitly snapshotted first request', async () => {
      userStore.token = 'snapshot-access'
      userStore.refreshToken = 'snapshot-refresh'
      const snapshot = userStore.captureCredentials()
      const config = await handlers.requestFulfilled({
        method: 'put', url: '/users/profile',
        headers: { Authorization: 'Bearer external', authorization: 'Bearer lowercase-external' },
        _sessionSnapshot: snapshot
      })

      expect(config.headers.Authorization).toBe('Bearer snapshot-access')
      expect(config.headers.authorization).toBeUndefined()
    })

    it('normalizes a real AxiosHeaders Authorization value to the captured snapshot', async () => {
      const { AxiosHeaders } = await vi.importActual('axios')
      const headers = new AxiosHeaders()
      headers.set('Authorization', 'Bearer external')
      headers.set('authorization', 'Bearer lowercase-external')
      userStore.token = 'snapshot-access'
      userStore.refreshToken = 'snapshot-refresh'
      const snapshot = userStore.captureCredentials()

      const config = await handlers.requestFulfilled({
        method: 'put', url: '/users/profile', headers, _sessionSnapshot: snapshot
      })

      expect(config.headers.get('Authorization')).toBe('Bearer snapshot-access')
      const authorizationKeys = Object.keys(config.headers.toJSON())
        .filter((key) => key.toLowerCase() === 'authorization')
      expect(authorizationKeys).toHaveLength(1)
      expect(authorizationKeys[0]).toBe('Authorization')
    })

    it('sends a valid snapshotted request when the session has no refresh token', async () => {
      userStore.token = 'access-without-refresh'
      userStore.refreshToken = ''
      const snapshot = userStore.captureCredentials()
      const config = await handlers.requestFulfilled({
        method: 'post', url: '/articles', headers: {}, _sessionSnapshot: snapshot
      })

      expect(config.headers.Authorization).toBe('Bearer access-without-refresh')
      expect(config._sessionSnapshot).toBe(snapshot)
    })

    it('removes any external Authorization header when an explicit snapshot has no access token', async () => {
      userStore.token = ''
      userStore.refreshToken = ''
      const snapshot = userStore.captureCredentials()
      const config = await handlers.requestFulfilled({
        method: 'post', url: '/articles',
        headers: { Authorization: 'Bearer external', authorization: 'Bearer lowercase-external' },
        _sessionSnapshot: snapshot
      })

      expect(config.headers.Authorization).toBeUndefined()
      expect(config.headers.authorization).toBeUndefined()
    })

    it('rejects a snapshotted first request after the durable identity changes', async () => {
      userStore.token = 'old-access'
      userStore.refreshToken = 'old-refresh'
      userStore.epoch = 'old-epoch'
      userStore.version = 'old-version'
      const snapshot = userStore.captureCredentials()
      localStorage.setItem('woniunote:auth-session', JSON.stringify({
        epoch: 'new-epoch', version: 'new-version', token: 'new-access',
        refreshToken: 'new-refresh', user: { userid: 2 }
      }))
      durableSessionEnabled = true

      await expect(handlers.requestFulfilled({
        method: 'post', url: '/articles', headers: {}, _sessionSnapshot: snapshot
      })).rejects.toMatchObject({
        message: '登录状态已变化，请重新登录', authSessionChanged: true
      })
      expect(apiInstance).not.toHaveBeenCalled()
    })

    it('rejects a stale snapshotted request after same-identity credentials rotate', async () => {
      userStore.token = 'old-access'
      userStore.refreshToken = 'old-refresh'
      userStore.epoch = 'same-epoch'
      userStore.version = 'old-version'
      const snapshot = userStore.captureCredentials()
      localStorage.setItem('woniunote:auth-session', JSON.stringify({
        epoch: 'same-epoch', version: 'new-version', token: 'rotated-access',
        refreshToken: 'rotated-refresh', user: { userid: 1 }
      }))
      durableSessionEnabled = true

      await expect(handlers.requestFulfilled({
        method: 'put', url: '/users/profile', headers: {}, _sessionSnapshot: snapshot
      })).rejects.toMatchObject({
        message: '登录状态已变化，请重新登录', authSessionChanged: true
      })
      expect(apiInstance).not.toHaveBeenCalled()
    })

    it('keeps public requests anonymous and available when IndexedDB session reads fail', async () => {
      userStore.syncSession.mockRejectedValueOnce(new Error('IndexedDB unavailable'))
      const config = await handlers.requestFulfilled({ method: 'get', url: '/articles', headers: {} })

      expect(config._sessionSyncFailed).toBe(true)
      expect(config.headers.Authorization).toBeUndefined()
      await expect(handlers.responseRejected({
        response: { status: 401, data: { message: 'anonymous request denied' } },
        config
      })).rejects.toMatchObject({ message: 'anonymous request denied' })
      expect(postMock).not.toHaveBeenCalled()
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('rejects a credentialed replay when authoritative session storage is unavailable', async () => {
      userStore.token = 'access-token'
      userStore.refreshToken = 'refresh-token'
      const snapshot = userStore.captureCredentials()
      userStore.syncSession.mockRejectedValueOnce(new Error('IndexedDB unavailable'))
      const config = {
        method: 'get', url: '/private', headers: {}, _retried: true, _sessionSnapshot: snapshot
      }

      await expect(handlers.requestFulfilled(config)).rejects.toMatchObject({
        message: '安全登录会话存储不可用，请重新登录后重试', authSessionChanged: true
      })
      expect(config.headers.Authorization).toBeUndefined()
      expect(postMock).not.toHaveBeenCalled()
    })

    it('does not attach session metadata to skipped or auth endpoint calls', async () => {
      const skipped = await handlers.requestFulfilled({
        method: 'post', url: '/private', headers: {}, skipAuthSession: true
      })
      const auth = await handlers.requestFulfilled({ method: 'post', url: '/auth/login', headers: {} })
      expect(skipped._sessionSnapshot).toBeUndefined()
      expect(auth._sessionSnapshot).toBeUndefined()
    })

    it('keeps a retry bound to its snapshot and rejects retries without one', async () => {
      userStore.token = 'abc'
      userStore.refreshToken = 'ref'
      const snapshot = userStore.captureCredentials()
      const replay = await handlers.requestFulfilled({
        method: 'get', url: '/private', headers: {}, _retried: true, _sessionSnapshot: snapshot
      })
      expect(replay.headers.Authorization).toBe('Bearer abc')
      await expect(handlers.requestFulfilled({
        method: 'get', url: '/private', headers: {}, _retried: true
      })).rejects.toMatchObject({ message: '登录状态已变化，请重新登录' })
    })

    it('stops loading once when a stale retry is rejected before dispatch', async () => {
      userStore.token = 'old-token'
      userStore.refreshToken = 'old-refresh'
      userStore.user = { userid: 1 }
      userStore.epoch = 'old-epoch'
      userStore.version = 'old-version'
      const staleSnapshot = {
        generation: 1, epoch: 'old-epoch', version: 'old-version', token: 'old-token',
        refreshToken: 'old-refresh', userIdentity: 'id:1', userId: 1
      }
      localStorage.setItem('woniunote:auth-session', JSON.stringify({
        epoch: 'new-epoch', version: 'new-version', token: 'new-token',
        refreshToken: 'new-refresh', user: { userid: 2 }
      }))
      durableSessionEnabled = true
      const staleConfig = {
        method: 'get', url: '/private', headers: {}, _retried: true,
        _sessionSnapshot: staleSnapshot
      }

      expect(startLoading).not.toHaveBeenCalled()
      const error = await handlers.requestFulfilled(staleConfig).then(
        () => null,
        (reason) => reason
      )
      expect(error).toMatchObject({
        message: '登录状态已变化，请重新登录', config: staleConfig
      })
      expect(error.config._loadingStarted).toBe(true)
      expect(startLoading).toHaveBeenCalledOnce()
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '登录状态已变化，请重新登录'
      })
      expect(stopLoading).toHaveBeenCalledOnce()
    })

    it('request error handler rejects', async () => {
      await expect(handlers.requestRejected(new Error('reqfail'))).rejects.toThrow('reqfail')
    })
  })

  describe('response interceptor (success path)', () => {
    it('returns payload when code === 200 and stops loading', () => {
      const resp = {
        data: { code: 200, message: 'ok', data: { v: 1 } },
        status: 200,
        config: { method: 'get', url: '/x', _loadingStarted: true, metadata: { startTime: Date.now() } }
      }
      const out = handlers.responseFulfilled(resp)
      expect(out).toEqual({ code: 200, message: 'ok', data: { v: 1 } })
      expect(stopLoading).toHaveBeenCalledOnce()
    })

    it('rejects with the server message on a real HTTP 400 response', async () => {
      const error = {
        response: { status: 400, data: { message: 'bad' } },
        config: { method: 'get', url: '/x', metadata: { startTime: Date.now() } }
      }
      await expect(handlers.responseRejected(error)).rejects.toThrow('bad')
      // Feedback is the caller's job now (notifyError); the interceptor stays silent.
      expect(elMessage).not.toHaveBeenCalled()
    })

    it('rejects contract-drift payloads (HTTP 200 + non-200 code) without toasting', async () => {
      const resp = {
        data: { code: 400, message: 'bad' },
        status: 200,
        config: { method: 'get', url: '/x', metadata: { startTime: Date.now() } }
      }
      await expect(handlers.responseFulfilled(resp)).rejects.toThrow('bad')
      expect(logWarning).toHaveBeenCalled()
      expect(elMessage).not.toHaveBeenCalled()
    })
  })

  describe('response interceptor (error path)', () => {
    it('maps 403 to permission message', async () => {
      const error = {
        response: { status: 403, data: {} },
        config: { method: 'get', url: '/x', metadata: { startTime: Date.now() } }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '没有权限执行此操作'
      })
    })

    it('maps 404 to not-found message', async () => {
      const error = {
        response: { status: 404, data: {} },
        config: { method: 'get', url: '/x' }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '请求的资源不存在'
      })
    })

    it('maps 429 using server message when present', async () => {
      const error = {
        response: { status: 429, data: { message: 'slow down' } },
        config: { method: 'get', url: '/x' }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({ message: 'slow down' })
    })

    it('maps network error (no response) to connection message', async () => {
      const error = { config: { method: 'get', url: '/x' } }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '网络错误，请检查网络连接'
      })
    })

    it('preserves backend error_code and request_id metadata', async () => {
      const error = {
        response: {
          status: 400,
          data: { data: { error_code: 'WRITE_OUTCOME_UNKNOWN', request_id: 'req-17' } }
        },
        config: { method: 'post', url: '/articles', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        errorCode: 'WRITE_OUTCOME_UNKNOWN',
        requestId: 'req-17'
      })
    })

    it('on 401 without refresh token: clears local session and routes to Login', async () => {
      userStore.refreshToken = ''
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(userStore.clearSession).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
    })

    it.each(['snapshot provider failure', 'localStorage quota failure'])(
      'still clears the expired session and routes to Login after %s', async (failure) => {
        userStore.refreshToken = ''
        routerCurrentRoute.value = { fullPath: '/write' }
        const unregister = registerEditorSnapshotProvider(1, () => {
          if (failure === 'snapshot provider failure') throw new Error('editor flush failed')
          return { headline: 'unsaved draft' }
        })
        const originalSetItem = localStorage.setItem.bind(localStorage)
        const setItem = vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
          if (failure === 'localStorage quota failure' &&
              String(key).startsWith('woniunote:editor-recovery:')) {
            throw new Error('QuotaExceededError')
          }
          return originalSetItem(key, value)
        })

        try {
          const error = {
            response: { status: 401, data: {} },
            config: { method: 'get', url: '/articles/my', headers: {} }
          }
          await expect(handlers.responseRejected(error)).rejects.toMatchObject({
            message: '登录已过期，请重新登录'
          })
          expect(userStore.clearSession).toHaveBeenCalledOnce()
          expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
          expect(elMessage).toHaveBeenCalledWith('登录已过期，浏览器未能保存未提交的编辑内容')
          if (failure === 'localStorage quota failure') {
            expect(setItem).toHaveBeenCalledWith(
              'woniunote:editor-recovery:1', expect.any(String)
            )
          }
        } finally {
          setItem.mockRestore()
          unregister()
        }
      }
    )

    it('still clears the expired session when the recovery warning cannot be displayed', async () => {
      userStore.refreshToken = ''
      routerCurrentRoute.value = { fullPath: '/write' }
      const unregister = registerEditorSnapshotProvider(1, () => ({ headline: 'unsaved draft' }))
      const originalSetItem = localStorage.setItem.bind(localStorage)
      const setItem = vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
        if (String(key).startsWith('woniunote:editor-recovery:')) {
          throw new Error('QuotaExceededError')
        }
        return originalSetItem(key, value)
      })
      elMessage.mockImplementationOnce(() => { throw new Error('message renderer unavailable') })

      try {
        const error = {
          response: { status: 401, data: {} },
          config: { method: 'get', url: '/articles/my', headers: {} }
        }
        await expect(handlers.responseRejected(error)).rejects.toMatchObject({
          message: '登录已过期，请重新登录'
        })

        expect(elMessage).toHaveBeenCalledWith('登录已过期，浏览器未能保存未提交的编辑内容')
        expect(userStore.clearSession).toHaveBeenCalledOnce()
        expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
        expect(logWarning).toHaveBeenCalledWith(
          '无法显示本地编辑恢复失败提示',
          { message: 'message renderer unavailable' }
        )
      } finally {
        setItem.mockRestore()
        unregister()
      }
    })

    it('does not redirect or clear a newer session when expiry cleanup loses the session race', async () => {
      userStore.refreshToken = ''
      routerCurrentRoute.value = { fullPath: '/write' }
      const unregister = registerEditorSnapshotProvider(1, async () => {
        userStore.token = 'newer-access-token'
        userStore.refreshToken = 'newer-refresh-token'
        userStore.user = { userid: 2 }
        userStore.epoch = 'epoch-2'
        userStore.sessionGeneration += 1
        return { headline: 'owner-1 unsaved draft' }
      })

      try {
        const error = {
          response: { status: 401, data: {} },
          config: { method: 'get', url: '/articles/my', headers: {} }
        }
        await expect(handlers.responseRejected(error)).rejects.toMatchObject({
          message: '登录已过期，请重新登录'
        })

        expect(userStore.clearSession).toHaveBeenCalledOnce()
        expect(userStore.user).toEqual({ userid: 2 })
        expect(userStore.token).toBe('newer-access-token')
        expect(routerPush).not.toHaveBeenCalled()
      } finally {
        unregister()
      }
    })

    it('does not redirect when session cleanup reports success but credentials remain', async () => {
      userStore.token = 'access-token-not-cleared'
      userStore.refreshToken = ''
      userStore.clearSession.mockResolvedValueOnce(true)

      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '登录已过期，请重新登录'
      })

      expect(userStore.clearSession).toHaveBeenCalledOnce()
      expect(userStore.token).toBe('access-token-not-cleared')
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('fails closed when a 401 cannot confirm the authoritative session before refresh', async () => {
      userStore.token = 'access-token'
      userStore.refreshToken = 'refresh-token'
      const snapshot = userStore.captureCredentials()
      userStore.syncSession.mockRejectedValueOnce(new Error('IndexedDB unavailable'))
      const error = {
        response: { status: 401, data: { message: 'expired' } },
        config: {
          method: 'get', url: '/articles/my', headers: {}, _sessionSnapshot: snapshot
        }
      }

      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '安全登录会话存储不可用，请重新登录后重试'
      })
      expect(postMock).not.toHaveBeenCalled()
      expect(apiInstance).not.toHaveBeenCalled()
      expect(userStore.clearSession).not.toHaveBeenCalled()
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('does not navigate to Login if the captured session was already replaced', async () => {
      userStore.refreshToken = ''
      userStore.clearSession.mockResolvedValueOnce(false)
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('does not attempt refresh on auth endpoints', async () => {
      userStore.refreshToken = 'r1'
      const error = {
        response: { status: 401, data: { message: 'bad creds' } },
        config: { method: 'post', url: '/auth/login', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeTruthy()
      expect(postMock).not.toHaveBeenCalled()
    })

    it('on 401 with refresh token: refreshes and replays original request', async () => {
      userStore.refreshToken = 'r1'
      postMock.mockResolvedValueOnce({
        data: { code: 200, data: { access_token: 'new-acc', refresh_token: 'new-ref' } }
      })
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      const out = await handlers.responseRejected(error)
      expect(postMock).toHaveBeenCalledWith('/api/auth/refresh', { refresh_token: 'r1' }, { timeout: 5000 })
      expect(userStore.setTokens).toHaveBeenCalledWith('new-acc', 'new-ref', expect.objectContaining({
        token: '', refreshToken: 'r1'
      }))
      // Original request replayed via api(config) → resolves to fake instance result.
      expect(out).toEqual({ replayed: true })
    })

    it('replays with the current same-session token after another request refreshed first', async () => {
      userStore.token = 'new-acc'
      userStore.refreshToken = 'r1'
      const oldSnapshot = {
        generation: userStore.sessionGeneration,
        epoch: userStore.epoch,
        version: userStore.version,
        token: 'old-acc',
        refreshToken: 'r1',
        userIdentity: 'id:1',
        userId: 1
      }
      const config = { method: 'get', url: '/articles/my', headers: {}, _sessionSnapshot: oldSnapshot }
      const out = await handlers.responseRejected({
        response: { status: 401, data: {} },
        config
      })
      expect(postMock).not.toHaveBeenCalled()
      expect(apiInstance).toHaveBeenCalledWith(expect.objectContaining({
        _retried: true,
        headers: expect.objectContaining({ Authorization: 'Bearer new-acc' })
      }))
      expect(out).toEqual({ replayed: true })
    })

    it('rechecks credentials after acquiring the cross-tab refresh lock and reuses a completed rotation', async () => {
      userStore.token = 'old-acc'
      userStore.refreshToken = 'r1'
      const lockRequest = vi.fn(async (name, callback) => {
        userStore.token = 'rotated-acc'
        userStore.refreshToken = 'rotated-ref'
        userStore.version = 'version-rotated'
        return callback()
      })
      const restoreLocks = installNavigatorLocks(lockRequest)
      try {
        const out = await handlers.responseRejected({
          response: { status: 401, data: {} },
          config: { method: 'get', url: '/articles/my', headers: {} }
        })

        expect(lockRequest).toHaveBeenCalledOnce()
        expect(lockRequest.mock.calls[0][0]).toBe('woniunote:auth-refresh-lock')
        expect(postMock).not.toHaveBeenCalled()
        expect(userStore.setTokens).not.toHaveBeenCalled()
        expect(apiInstance).toHaveBeenCalledWith(expect.objectContaining({
          _retried: true,
          headers: expect.objectContaining({ Authorization: 'Bearer rotated-acc' })
        }))
        expect(out).toEqual({ replayed: true })
      } finally {
        restoreLocks()
      }
    })

    it('does not refresh an old session after a new login wins while waiting for the refresh lock', async () => {
      userStore.token = 'old-acc'
      userStore.refreshToken = 'r1'
      const lockRequest = vi.fn(async (name, callback) => {
        userStore.sessionGeneration += 1
        userStore.epoch = 'new-login-epoch'
        userStore.version = 'new-login-version'
        userStore.token = 'new-login-access'
        userStore.refreshToken = 'new-login-refresh'
        userStore.user = { userid: 2 }
        return callback()
      })
      const restoreLocks = installNavigatorLocks(lockRequest)
      try {
        await expect(handlers.responseRejected({
          response: { status: 401, data: {} },
          config: { method: 'get', url: '/articles/my', headers: {} }
        })).rejects.toMatchObject({ message: '登录已过期，请重新登录' })

        expect(lockRequest).toHaveBeenCalledOnce()
        expect(postMock).not.toHaveBeenCalled()
        expect(userStore.clearSession).toHaveBeenCalledOnce()
        expect(userStore.token).toBe('new-login-access')
        expect(userStore.refreshToken).toBe('new-login-refresh')
        expect(routerPush).not.toHaveBeenCalled()
        expect(apiInstance).not.toHaveBeenCalled()
      } finally {
        restoreLocks()
      }
    })

    it('on 401 with failing refresh: clears local session and routes to Login', async () => {
      userStore.refreshToken = 'r1'
      postMock.mockRejectedValueOnce(new Error('refresh down'))
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(userStore.clearSession).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
    })

    it('does not retry the same request twice (_retried guard)', async () => {
      userStore.refreshToken = 'r1'
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {}, _retried: true }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeTruthy()
      expect(postMock).not.toHaveBeenCalled()
    })

    it('stops loading on the error path when the request had started it', async () => {
      const error = {
        response: { status: 500, data: {} },
        config: { method: 'get', url: '/x', _loadingStarted: true, metadata: { startTime: Date.now() } }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeTruthy()
      expect(stopLoading).toHaveBeenCalledOnce()
    })

    it('tolerates a config without metadata when computing duration', () => {
      const resp = {
        data: { code: 200, data: { ok: true } },
        status: 200,
        config: { method: 'get', url: '/x' }
      }
      expect(handlers.responseFulfilled(resp)).toEqual({ code: 200, data: { ok: true } })
    })

    it('falls back to the generic message when an HTTP error omits the server message', async () => {
      const error = {
        response: { status: 500, data: {} },
        config: { method: 'get', url: '/x', metadata: { startTime: Date.now() } }
      }
      // The rejected Error carries the generic 请求失败 message; callers surface it.
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '请求失败'
      })
      expect(elMessage).not.toHaveBeenCalled()
    })

    it('maps 429 to the default throttle message when the server omits one', async () => {
      const error = {
        response: { status: 429, data: {} },
        config: { method: 'get', url: '/x' }
      }
      await expect(handlers.responseRejected(error)).rejects.toMatchObject({
        message: '请求过于频繁，请稍后再试'
      })
    })

    it('treats a non-200 refresh payload as a failed refresh', async () => {
      userStore.refreshToken = 'r1'
      postMock.mockResolvedValueOnce({ data: { code: 401, message: 'expired', data: null } })
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(userStore.setTokens).not.toHaveBeenCalled()
      expect(userStore.clearSession).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
    })

    it('bails out without clearing after the store refresh token disappears mid-flight', async () => {
      // The 401 guard reads refreshToken once; by the time refreshAccessToken
      // reads it again the value can be gone (concurrent logout). Cover the
      // `if (!rt) return null` guard with a one-shot getter.
      let reads = 0
      Object.defineProperty(userStore, 'refreshToken', {
        configurable: true,
        get() { reads += 1; return reads === 1 ? 'r1' : '' }
      })
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(postMock).not.toHaveBeenCalled()
      expect(userStore.clearSession).not.toHaveBeenCalled()
      Object.defineProperty(userStore, 'refreshToken', { configurable: true, enumerable: true, writable: true, value: '' })
    })

    it('queues concurrent 401s behind a single in-flight refresh', async () => {
      userStore.refreshToken = 'r1'
      let releaseRefresh
      postMock.mockImplementationOnce(() => new Promise((resolve) => { releaseRefresh = resolve }))

      const first = handlers.responseRejected({
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      })
      // Second 401 arrives while the first refresh is still pending → queued.
      const second = handlers.responseRejected({
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/2', headers: {} }
      })
      await vi.waitFor(() => expect(postMock).toHaveBeenCalledOnce())
      expect(postMock).toHaveBeenCalledTimes(1)

      releaseRefresh({ data: { code: 200, data: { access_token: 'new-acc', refresh_token: 'new-ref' } } })

      await expect(first).resolves.toEqual({ replayed: true })
      await expect(second).resolves.toEqual({ replayed: true })
      expect(postMock).toHaveBeenCalledTimes(1) // only one refresh for both 401s
      expect(apiInstance).toHaveBeenCalledTimes(2) // both requests replayed
    })

    it('rejects queued 401s when the shared refresh fails', async () => {
      userStore.refreshToken = 'r1'
      let releaseRefresh
      postMock.mockImplementationOnce(() => new Promise((resolve) => { releaseRefresh = resolve }))

      const first = handlers.responseRejected({
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      })
      const second = handlers.responseRejected({
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/2', headers: {} }
      })

      await vi.waitFor(() => expect(releaseRefresh).toBeTypeOf('function'))
      releaseRefresh({ data: { code: 500, data: null } })

      await expect(first).rejects.toBeInstanceOf(Error)
      await expect(second).rejects.toMatchObject({ message: '登录已过期，请重新登录' })
      expect(userStore.clearSession).toHaveBeenCalled()
    })
  })

  it('does not refresh or replay a 401 from an older identity when durable storage changed before its event', async () => {
    userStore.token = 'old-token'
    userStore.refreshToken = 'old-refresh'
    userStore.user = { userid: 1 }
    userStore.sessionGeneration = 1
    userStore.epoch = 'old-epoch'
    userStore.version = 'old-version'
    const oldSharedSession = {
      epoch: 'old-epoch', version: 'old-version', token: 'old-token',
      refreshToken: 'old-refresh', user: { userid: 1 }
    }
    const oldSnapshot = {
      generation: 1, epoch: 'old-epoch', token: 'old-token',
      refreshToken: 'old-refresh', userIdentity: 'id:1', userId: 1
    }
    localStorage.setItem('woniunote:auth-session', JSON.stringify(oldSharedSession))
    localStorage.setItem('token', 'old-token')
    const newSharedSession = {
      epoch: 'new-epoch', version: 'new-version', token: 'new-token',
      refreshToken: 'new-refresh', user: { userid: 2 }
    }
    localStorage.setItem('woniunote:auth-session', JSON.stringify(newSharedSession))
    localStorage.setItem('token', 'new-token')
    durableSessionEnabled = true
    const error = {
      response: { status: 401, data: {} },
      config: { method: 'get', url: '/articles/my', headers: {}, _sessionSnapshot: oldSnapshot }
    }

    await expect(handlers.responseRejected(error)).rejects.toMatchObject({
      message: '登录状态已变化，请重新登录'
    })
    expect(postMock).not.toHaveBeenCalled()
    expect(apiInstance).not.toHaveBeenCalled()
    expect(userStore.clearSession).not.toHaveBeenCalled()
  })

  it('rejects a replay at dispatch if durable credentials changed after the 401 check', async () => {
    userStore.token = 'old-token'
    userStore.refreshToken = 'old-refresh'
    userStore.user = { userid: 1 }
    userStore.sessionGeneration = 1
    userStore.epoch = 'old-epoch'
    userStore.version = 'old-version'
    const snapshot = {
      generation: 1, epoch: 'old-epoch', version: 'old-version', token: 'old-token',
      refreshToken: 'old-refresh', userIdentity: 'id:1', userId: 1
    }
    localStorage.setItem('woniunote:auth-session', JSON.stringify({
      epoch: 'new-epoch', version: 'new-version', token: 'new-token',
      refreshToken: 'new-refresh', user: { userid: 2 }
    }))
    durableSessionEnabled = true

    await expect(handlers.requestFulfilled({
      method: 'get', url: '/articles/my', headers: {}, _retried: true, _sessionSnapshot: snapshot
    })).rejects.toMatchObject({ message: '登录状态已变化，请重新登录' })
  })

  it('does not apply a late refresh after durable storage changes before its event', async () => {
    userStore.token = 'old-token'
    userStore.refreshToken = 'old-refresh'
    userStore.user = { userid: 1 }
    userStore.sessionGeneration = 1
    userStore.epoch = 'old-epoch'
    userStore.version = 'old-version'
    const snapshot = {
      generation: 1, epoch: 'old-epoch', version: 'old-version', token: 'old-token',
      refreshToken: 'old-refresh', userIdentity: 'id:1', userId: 1
    }
    localStorage.setItem('woniunote:auth-session', JSON.stringify({
      epoch: 'old-epoch', version: 'old-version', token: 'old-token',
      refreshToken: 'old-refresh', user: { userid: 1 }
    }))
    durableSessionEnabled = true
    let releaseRefresh
    postMock.mockImplementationOnce(() => new Promise((resolve) => { releaseRefresh = resolve }))

    const pending = handlers.responseRejected({
      response: { status: 401, data: {} },
      config: { method: 'get', url: '/articles/my', headers: {}, _sessionSnapshot: snapshot }
    })
    await vi.waitFor(() => expect(postMock).toHaveBeenCalledOnce())
    localStorage.setItem('woniunote:auth-session', JSON.stringify({
      epoch: 'new-epoch', version: 'new-version', token: 'new-token',
      refreshToken: 'new-refresh', user: { userid: 2 }
    }))
    localStorage.setItem('token', 'new-token')
    releaseRefresh({ data: { code: 200, data: { access_token: 'late-token', refresh_token: 'late-refresh' } } })

    await expect(pending).rejects.toMatchObject({ message: '登录已过期，请重新登录' })
    expect(userStore.token).toBe('new-token')
    expect(userStore.user).toMatchObject({ userid: 2 })
    expect(apiInstance).not.toHaveBeenCalled()
  })

  it('does not refresh on logout 401', async () => {
    userStore.refreshToken = 'refresh'
    await expect(handlers.responseRejected({
      response: { status: 401, data: {} },
      config: { method: 'post', url: '/auth/logout', headers: {} }
    })).rejects.toBeTruthy()
    expect(postMock).not.toHaveBeenCalled()
    expect(userStore.clearSession).not.toHaveBeenCalled()
  })

  describe('api endpoint wrappers', () => {
    it('default export is the axios instance', () => {
      expect(apiDefault).toBe(apiInstance)
    })

    it('authApi calls correct endpoints', () => {
      authApi.login({ u: 1 })
      authApi.register({ u: 1 })
      authApi.getMe()
      authApi.logout()
      authApi.refresh('rt')
      expect(apiInstance.post).toHaveBeenCalledWith('/auth/login', { u: 1 })
      expect(apiInstance.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'rt' })
      expect(apiInstance.post).toHaveBeenCalledWith('/auth/logout', {}, {
        skipAuthSession: true, headers: {}
      })
      expect(apiInstance.get).toHaveBeenCalledWith('/auth/me')
    })

    it('logout sends the captured refresh token and access authorization', () => {
      authApi.logout({ token: 'captured-access', refreshToken: 'captured-refresh' })
      expect(apiInstance.post).toHaveBeenCalledWith('/auth/logout', {
        refresh_token: 'captured-refresh'
      }, {
        skipAuthSession: true,
        headers: { Authorization: 'Bearer captured-access' }
      })
    })

    it('articleApi builds parameterized URLs', () => {
      articleApi.getList({ page: 1 })
      articleApi.getDetail(7)
      articleApi.update(7, { t: 1 })
      articleApi.updateType(7, 101)
      articleApi.delete(7)
      articleApi.toggleRecommend(7)
      expect(apiInstance.get).toHaveBeenCalledWith('/articles', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/7')
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7', { t: 1 })
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7/type', { type: 101 })
      expect(apiInstance.delete).toHaveBeenCalledWith('/articles/7')
    })

    it('forwards a captured session snapshot through mutation and detail wrappers', () => {
      const config = { _sessionSnapshot: { epoch: 'captured-epoch', token: 'captured-token' } }
      articleApi.getDetail(7, config)
      articleApi.create({ headline: 'h' }, config)
      articleApi.update(7, { headline: 'h' }, config)
      userApi.updateProfile({ nickname: 'n' }, config)
      userApi.updatePassword({ old_password: 'old' }, config)

      expect(apiInstance.get).toHaveBeenCalledWith('/articles/7', config)
      expect(apiInstance.post).toHaveBeenCalledWith('/articles', { headline: 'h' }, config)
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7', { headline: 'h' }, config)
      expect(apiInstance.put).toHaveBeenCalledWith('/users/profile', { nickname: 'n' }, config)
      expect(apiInstance.post).toHaveBeenCalledWith('/users/password', { old_password: 'old' }, config)
    })

    it('preserves the captured session snapshot in multipart upload wrappers', () => {
      const file = new Blob(['x'], { type: 'image/png' })
      const config = { _sessionSnapshot: { epoch: 'captured-epoch', token: 'captured-token' } }
      uploadApi.uploadImage(file, config)
      uploadApi.uploadAvatar(file, config)

      const calls = apiInstance.post.mock.calls.filter((call) => call[0].startsWith('/upload'))
      expect(calls.filter((call) => call[0] === '/upload/image')[0][2]).toMatchObject(config)
      expect(calls.filter((call) => call[0] === '/upload/avatar')[0][2]).toMatchObject(config)
      expect(calls.every((call) => call[2].headers['Content-Type'] === 'multipart/form-data')).toBe(true)
    })

    it('commentApi vote helpers send the right vote_type', () => {
      commentApi.agree(3)
      commentApi.oppose(3)
      expect(apiInstance.post).toHaveBeenCalledWith('/comments/3/vote', { vote_type: 1 })
      expect(apiInstance.post).toHaveBeenCalledWith('/comments/3/vote', { vote_type: -1 })
    })

    it('favoriteApi add/remove/check', () => {
      favoriteApi.add(9)
      favoriteApi.remove(9)
      favoriteApi.check(9)
      expect(apiInstance.post).toHaveBeenCalledWith('/favorites', { articleid: 9 })
      expect(apiInstance.delete).toHaveBeenCalledWith('/favorites/9')
      expect(apiInstance.get).toHaveBeenCalledWith('/favorites/check/9')
    })

    it('uploadApi sends multipart form data', () => {
      const file = new Blob(['x'], { type: 'image/png' })
      uploadApi.uploadImage(file)
      uploadApi.uploadFile(file)
      uploadApi.uploadAvatar(file)
      const calls = apiInstance.post.mock.calls.filter((c) => c[0].startsWith('/upload'))
      expect(calls.length).toBe(3)
      expect(calls[0][2].headers['Content-Type']).toBe('multipart/form-data')
      expect(calls[0][1]).toBeInstanceOf(FormData)
    })

    it('remaining domain wrappers hit expected paths', () => {
      userApi.getProfile(1)
      userApi.updateProfile({ a: 1 })
      userApi.updatePassword({ p: 1 })
      creditApi.getSummary()
      creditApi.payArticle(2)
      adminApi.getStats()
      myCommentApi.getMyComments({ page: 1 })
      draftApi.getMyDrafts({ page: 1 })
      systemApi.healthCheck()
      mathTrainingApi.getSummary()
      expect(apiInstance.get).toHaveBeenCalledWith('/users/1')
      expect(apiInstance.put).toHaveBeenCalledWith('/users/profile', { a: 1 })
      expect(apiInstance.get).toHaveBeenCalledWith('/credits/balance')
      expect(apiInstance.post).toHaveBeenCalledWith('/credits/pay-article/2')
      expect(apiInstance.get).toHaveBeenCalledWith('/admin/stats')
      expect(apiInstance.get).toHaveBeenCalledWith('/system/health')
      expect(apiInstance.get).toHaveBeenCalledWith('/math-training/summary')
    })

    it('article list/type helpers hit expected paths', () => {
      articleApi.getMyList({ page: 2 })
      articleApi.getHot()
      articleApi.getTypes()
      articleApi.create({ headline: 'h' })
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/my', { params: { page: 2 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/hot')
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/types')
      expect(apiInstance.post).toHaveBeenCalledWith('/articles', { headline: 'h' })
    })

    it('comment list/create/delete helpers hit expected paths', () => {
      commentApi.getByArticle(5, { page: 1 })
      commentApi.create({ content: 'c' })
      commentApi.delete(6)
      expect(apiInstance.get).toHaveBeenCalledWith('/comments/article/5', { params: { page: 1 } })
      expect(apiInstance.post).toHaveBeenCalledWith('/comments', { content: 'c' })
      expect(apiInstance.delete).toHaveBeenCalledWith('/comments/6')
    })

    it('favorite list and credit history/status helpers hit expected paths', () => {
      favoriteApi.getList({ page: 1 })
      creditApi.getList({ page: 3 })
      creditApi.checkArticle(4)
      expect(apiInstance.get).toHaveBeenCalledWith('/favorites', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/credits/history', { params: { page: 3 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/credits/check-article/4')
    })

    it('admin user/article moderation helpers hit expected paths', () => {
      adminApi.getUsers({ page: 1 })
      adminApi.toggleHide(7)
      adminApi.toggleCheck(7)
      adminApi.toggleRecommend(7)
      expect(apiInstance.get).toHaveBeenCalledWith('/admin/users', { params: { page: 1 } })
      expect(apiInstance.post).toHaveBeenCalledWith('/articles/7/hide')
      expect(apiInstance.post).toHaveBeenCalledWith('/articles/7/check')
      expect(apiInstance.post).toHaveBeenCalledWith('/articles/7/recommend')
    })

    it('system monitoring helpers hit expected paths', () => {
      systemApi.getStatus()
      systemApi.getDatabase()
      expect(apiInstance.get).toHaveBeenCalledWith('/system/status')
      expect(apiInstance.get).toHaveBeenCalledWith('/system/db')
    })

    it('math training helpers hit expected paths', () => {
      mathTrainingApi.createRecord({ correct_count: 1 })
      mathTrainingApi.getRecords({ page: 1 })
      mathTrainingApi.getRecordDetail(8)
      mathTrainingApi.getWrongAnswers({ page: 2 })
      expect(apiInstance.post).toHaveBeenCalledWith('/math-training/records', { correct_count: 1 })
      expect(apiInstance.get).toHaveBeenCalledWith('/math-training/records', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/math-training/records/8')
      expect(apiInstance.get).toHaveBeenCalledWith('/math-training/wrong-answers', { params: { page: 2 } })
    })

    it('admin category wrappers hit expected paths', () => {
      adminApi.getArticles({ page: 1 })
      adminApi.getArticleCategories()
      adminApi.createArticleCategory({ name: '新分类' })
      adminApi.updateArticleCategory(9, { name: '改名' })
      adminApi.deleteArticleCategory(9, { move_articles_to: 1 })
      adminApi.updateArticleType(7, 101)

      expect(apiInstance.get).toHaveBeenCalledWith('/admin/articles', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/admin/article-categories')
      expect(apiInstance.post).toHaveBeenCalledWith('/admin/article-categories', { name: '新分类' })
      expect(apiInstance.put).toHaveBeenCalledWith('/admin/article-categories/9', { name: '改名' })
      expect(apiInstance.delete).toHaveBeenCalledWith('/admin/article-categories/9', { params: { move_articles_to: 1 } })
      expect(apiInstance.put).toHaveBeenCalledWith('/admin/articles/7/type', { type: 101 })
    })
  })
})
