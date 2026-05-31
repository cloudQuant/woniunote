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

const elMessageError = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: { error: (...a) => elMessageError(...a) }
}))

const routerPush = vi.fn()
vi.mock('@/router', () => ({
  default: { push: (...a) => routerPush(...a) }
}))

const userStore = {
  token: '',
  refreshToken: '',
  setTokens: vi.fn(),
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

// Import after mocks so interceptors register against the fake instance.
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
    userStore.refreshToken = ''
  })

  describe('request interceptor', () => {
    it('starts loading and injects Authorization when token present', () => {
      userStore.token = 'abc'
      const cfg = handlers.requestFulfilled({ method: 'get', url: '/x', headers: {} })
      expect(startLoading).toHaveBeenCalledOnce()
      expect(cfg._loadingStarted).toBe(true)
      expect(cfg.headers.Authorization).toBe('Bearer abc')
      expect(cfg.metadata.startTime).toBeTypeOf('number')
    })

    it('skips loading when config.skipLoading is set', () => {
      const cfg = handlers.requestFulfilled({ method: 'get', url: '/x', headers: {}, skipLoading: true })
      expect(startLoading).not.toHaveBeenCalled()
      expect(cfg._loadingStarted).toBeUndefined()
    })

    it('omits Authorization when no token', () => {
      const cfg = handlers.requestFulfilled({ method: 'get', url: '/x', headers: {} })
      expect(cfg.headers.Authorization).toBeUndefined()
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

    it('rejects and shows message when business code !== 200', async () => {
      const resp = {
        data: { code: 400, message: 'bad' },
        status: 200,
        config: { method: 'get', url: '/x', metadata: { startTime: Date.now() } }
      }
      await expect(handlers.responseFulfilled(resp)).rejects.toThrow('bad')
      expect(elMessageError).toHaveBeenCalledWith('bad')
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

    it('on 401 without refresh token: logs out and routes to Login', async () => {
      userStore.refreshToken = ''
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(userStore.logout).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
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
      expect(postMock).toHaveBeenCalledWith('/api/auth/refresh', { refresh_token: 'r1' })
      expect(userStore.setTokens).toHaveBeenCalledWith('new-acc', 'new-ref')
      // Original request replayed via api(config) → resolves to fake instance result.
      expect(out).toEqual({ replayed: true })
    })

    it('on 401 with failing refresh: logs out and routes to Login', async () => {
      userStore.refreshToken = 'r1'
      postMock.mockRejectedValueOnce(new Error('refresh down'))
      const error = {
        response: { status: 401, data: {} },
        config: { method: 'get', url: '/articles/my', headers: {} }
      }
      await expect(handlers.responseRejected(error)).rejects.toBeInstanceOf(Error)
      expect(userStore.logout).toHaveBeenCalled()
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
      expect(apiInstance.get).toHaveBeenCalledWith('/auth/me')
    })

    it('articleApi builds parameterized URLs', () => {
      articleApi.getList({ page: 1 })
      articleApi.getDetail(7)
      articleApi.update(7, { t: 1 })
      articleApi.delete(7)
      articleApi.toggleRecommend(7)
      expect(apiInstance.get).toHaveBeenCalledWith('/articles', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/7')
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7', { t: 1 })
      expect(apiInstance.delete).toHaveBeenCalledWith('/articles/7')
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
  })
})
