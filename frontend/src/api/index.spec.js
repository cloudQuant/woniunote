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
  ElMessage: Object.assign((...a) => elMessage(...a), { error: (...a) => elMessage(...a) })
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
import { logWarning } from '@/utils/logger'
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
      expect(postMock).toHaveBeenCalledWith('/api/auth/refresh', { refresh_token: 'r1' }, { timeout: 5000 })
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
      expect(userStore.logout).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalledWith({ name: 'Login' })
    })

    it('bails out of the refresh when the store token disappears mid-flight', async () => {
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
      expect(userStore.logout).toHaveBeenCalled()
      delete userStore.refreshToken
      userStore.refreshToken = ''
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

      releaseRefresh({ data: { code: 500, data: null } })

      await expect(first).rejects.toBeInstanceOf(Error)
      await expect(second).rejects.toMatchObject({ message: '登录已过期，请重新登录' })
      expect(userStore.logout).toHaveBeenCalled()
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
      articleApi.updateType(7, 101)
      articleApi.delete(7)
      articleApi.toggleRecommend(7)
      expect(apiInstance.get).toHaveBeenCalledWith('/articles', { params: { page: 1 } })
      expect(apiInstance.get).toHaveBeenCalledWith('/articles/7')
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7', { t: 1 })
      expect(apiInstance.put).toHaveBeenCalledWith('/articles/7/type', { type: 101 })
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
