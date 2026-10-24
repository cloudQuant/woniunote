/**
 * @module api
 * @description 全局 API 接口封装模块
 * 包含 Axios 实例配置、拦截器处理以及各个业务模块的 API 定义。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'
import { safeInternalRedirect } from '@/utils/authNavigation'
import { saveEditorRecovery } from '@/utils/editorRecovery'
import { logInfo, logError, logWarning, logRequest } from '@/utils/logger'
import { startLoading, stopLoading } from '@/utils/loading'

/**
 * 创建 Axios 实例
 * @type {import('axios').AxiosInstance}
 */
const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Refresh is shared only by requests from the same credential snapshot.
let refreshState = null
const REFRESH_LOCK_NAME = 'woniunote:auth-refresh-lock'

function isAuthEndpoint(url = '') {
  return /\/auth\/(?:login|register|refresh|logout)(?:\?|$)/.test(url)
}

function sameCredentialSnapshot(left, right) {
  return !!left && !!right && left.generation === right.generation &&
    left.token === right.token && left.refreshToken === right.refreshToken &&
    left.userIdentity === right.userIdentity
}

function stopLoadingFor(config) {
  if (config?._loadingStarted) {
    config._loadingStarted = false
    stopLoading()
  }
}

function bindAuthorizationToSnapshot(config, snapshot) {
  const headers = config.headers ||= {}
  if (typeof headers.delete === 'function') {
    // AxiosHeaders.delete is case-insensitive and avoids retaining a second
    // authorization spelling when a caller supplied differently-cased keys.
    headers.delete('Authorization')
  } else {
    for (const key of Object.keys(headers)) {
      if (key.toLowerCase() === 'authorization') delete headers[key]
    }
  }

  if (!snapshot?.token) return
  const value = `Bearer ${snapshot.token}`
  if (typeof headers.set === 'function') headers.set('Authorization', value)
  else headers.Authorization = value
}

/**
 * 用 refresh_token 静默换取新的 access_token。
 * 直接用裸 axios，避免触发本实例拦截器导致递归。
 * @returns {Promise<Object|null>} 新凭据快照；失败或凭据已变化时返回 null
 */
async function refreshAccessToken(snapshot) {
  const userStore = useUserStore()
  if (!snapshot?.refreshToken) return null

  const refreshUnderLock = async () => {
    // The lock is separate from the session-mutation lock: keep the refresh
    // network request out of the latter, then let setTokens acquire it only
    // for the short durable commit.
    await userStore.syncSession()
    const currentSnapshot = userStore.captureCredentials()
    if (!userStore.isSessionCurrent(snapshot)) return null

    if (!userStore.isCredentialsCurrent(snapshot)) {
      // Another tab may have completed the rotation while this tab waited for
      // the refresh lock. Reuse only a complete, current credential pair from
      // the same session; never send the now-stale refresh token a second time.
      if (currentSnapshot.token && currentSnapshot.refreshToken &&
          (currentSnapshot.token !== snapshot.token ||
           currentSnapshot.refreshToken !== snapshot.refreshToken) &&
          userStore.isCredentialsCurrent(currentSnapshot)) {
        return currentSnapshot
      }
      return null
    }

    if (!currentSnapshot.refreshToken) return null

    let resp
    try {
      resp = await axios.post(
        '/api/auth/refresh',
        { refresh_token: currentSnapshot.refreshToken },
        { timeout: 5000 }
      )
    } catch (error) {
      logWarning('访问令牌刷新请求失败', { message: error?.message || '未知错误' })
      return null
    }

    const data = resp.data
    if (data?.code === 200 && data.data?.access_token && data.data?.refresh_token) {
      const updated = await userStore.setTokens(
        data.data.access_token,
        data.data.refresh_token,
        currentSnapshot
      )
      if (!updated || !userStore.isSessionCurrent(snapshot)) return null
      const committedSnapshot = userStore.captureCredentials()
      return userStore.isCredentialsCurrent(committedSnapshot) ? committedSnapshot : null
    }
    return null
  }

  const locks = typeof navigator === 'undefined' ? null : navigator.locks
  if (locks?.request) {
    return locks.request(REFRESH_LOCK_NAME, refreshUnderLock)
  }

  // Without Web Locks, refreshState still coalesces requests in this tab and
  // the store's credential fence protects commits. Cross-tab refresh
  // serialization is unavailable in this fallback and is not guaranteed.
  return refreshUnderLock()
}

function refreshForSnapshot(snapshot) {
  if (refreshState && sameCredentialSnapshot(refreshState.snapshot, snapshot)) {
    return refreshState.promise
  }

  const state = { snapshot, promise: null }
  state.promise = refreshAccessToken(snapshot).finally(() => {
    if (refreshState === state) refreshState = null
  })
  refreshState = state
  return state.promise
}

function loginLocation() {
  const currentPath = router.currentRoute?.value?.fullPath
  const redirect = safeInternalRedirect(currentPath, router)
  return redirect
    ? { name: 'Login', query: { redirect } }
    : { name: 'Login' }
}

async function expireSession(snapshot, userStore) {
  const currentPath = router.currentRoute?.value?.fullPath
  if (snapshot?.userId !== null && snapshot?.userId !== undefined && currentPath) {
    try {
      await saveEditorRecovery(snapshot.userId, currentPath)
    } catch (error) {
      logWarning('会话过期时无法保存本地编辑恢复稿', {
        message: error?.message || '未知错误'
      })
      try {
        ElMessage.warning('登录已过期，浏览器未能保存未提交的编辑内容')
      } catch (messageError) {
        logWarning('无法显示本地编辑恢复失败提示', {
          message: messageError?.message || '未知错误'
        })
      }
    }
  }

  if (!await userStore.clearSession(snapshot)) return false
  const clearedGeneration = userStore.sessionGeneration
  const clearedSnapshot = userStore.captureCredentials()
  if (clearedSnapshot.token || clearedSnapshot.refreshToken ||
      clearedSnapshot.generation !== clearedGeneration) return false
  await router.push(loginLocation())
  return true
}

/**
 * 请求拦截器
 * 处理 Token 注入和请求日志记录
 */
api.interceptors.request.use(
  async config => {
    // 记录请求开始时间
    config.metadata = { startTime: Date.now() }

    // 全局 loading（除非显式跳过，如静默刷新/轮询）
    if (!config.skipLoading) {
      startLoading()
      config._loadingStarted = true
    }

    try {
      const userStore = useUserStore()
      config.headers ||= {}
      if (!config.skipAuthSession && !isAuthEndpoint(config.url)) {
        try {
          await userStore.syncSession()
        } catch (error) {
          if (config._retried || config._sessionSnapshot || config.headers.Authorization) {
            const unavailable = buildError('安全登录会话存储不可用，请重新登录后重试', {
              config,
              response: error?.response
            })
            unavailable.authSessionChanged = true
            throw unavailable
          }

          // An unauthenticated public request may proceed anonymously when
          // durable session storage is unavailable. Never retain a stale
          // Authorization header or attempt refresh/replay in this state.
          config._sessionSyncFailed = true
          delete config.headers.Authorization
          delete config.headers.authorization
          logWarning('登录会话不可用，本次请求将以匿名方式发送')
        }
        if (config._sessionSyncFailed) {
          logInfo(`API请求开始: ${config.method?.toUpperCase()} ${config.url}`)
          return config
        }
        if (config._retried) {
          // Keep a replay attached to the credentials that authorized it. A
          // session change between response handling and dispatch must reject
          // this request instead of rebinding its payload to another identity.
          if (!config._sessionSnapshot || !userStore.isCredentialsCurrent(config._sessionSnapshot)) {
            const error = buildError('登录状态已变化，请重新登录', { config })
            error.authSessionChanged = true
            throw error
          }
          bindAuthorizationToSnapshot(config, config._sessionSnapshot)
        } else if (!config._sessionSnapshot) {
          const snapshot = userStore.captureCredentials()
          config._sessionSnapshot = snapshot
          if (snapshot.token && !config.headers.Authorization) {
            config.headers.Authorization = `Bearer ${snapshot.token}`
          }
        } else {
          if (!userStore.isCredentialsCurrent(config._sessionSnapshot)) {
            const error = buildError('登录状态已变化，请重新登录', { config })
            error.authSessionChanged = true
            throw error
          }
          bindAuthorizationToSnapshot(config, config._sessionSnapshot)
        }
      }

      logInfo(`API请求开始: ${config.method?.toUpperCase()} ${config.url}`)
      return config
    } catch (error) {
      error.config ||= config
      throw error
    }
  },
  error => {
    stopLoadingFor(error.config)
    logError('请求拦截器错误', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * 处理响应日志、错误统一处理和 Token 过期无感刷新
 */
api.interceptors.response.use(
  response => {
    stopLoadingFor(response.config)

    // 计算请求耗时
    const duration = Date.now() - (response.config.metadata?.startTime || Date.now())
    const method = response.config.method?.toUpperCase()
    const url = response.config.url

    logRequest(method, url, response.status, duration)

    const data = response.data
    if (data.code !== 200) {
      // 契约漂移防御：后端错误恒为 4xx/5xx，此分支理论上不可达。
      // 只记日志并 reject，用户提示交给调用方的 notifyError（不注入通用兜底）。
      logWarning(`API响应异常: ${method} ${url}`, { code: data.code, message: data.message })
      return Promise.reject(buildError(data.message, {
        response: { status: response.status, data }
      }))
    }
    return data
  },
  async error => {
    stopLoadingFor(error.config)

    // A pre-dispatch auth fence has already produced the user-facing reason.
    // Keep it intact while still balancing the loading counter above.
    if (error.authSessionChanged) return Promise.reject(error)

    // 计算请求耗时
    const duration = Date.now() - (error.config?.metadata?.startTime || Date.now())
    const method = error.config?.method?.toUpperCase()
    const url = error.config?.url

    let errorMessage = '请求失败'

    if (error.response) {
      const status = error.response.status
      errorMessage = error.response.data?.detail || error.response.data?.message || '请求失败'

      logRequest(method, url, status, duration)

      const originalConfig = error.config
      const authEndpoint = isAuthEndpoint(url)

      // 401：尝试用 refresh_token 无感刷新并重放原请求（每个请求只重试一次）
      if (status === 401 && !authEndpoint && originalConfig && !originalConfig._retried) {
        if (originalConfig._sessionSyncFailed) {
          return Promise.reject(buildError(errorMessage, error))
        }
        const userStore = useUserStore()
        const originalSnapshot = originalConfig?._sessionSnapshot || userStore.captureCredentials()
        try {
          await userStore.syncSession()
        } catch (sessionError) {
          logWarning('401处理时无法确认登录会话，已阻止刷新和重放', {
            message: sessionError?.message || '未知错误'
          })
          return Promise.reject(buildError('安全登录会话存储不可用，请重新登录后重试', {
            config: originalConfig
          }))
        }

        // An older response must never refresh, replay, or clear a newer identity.
        if (!userStore.isSessionCurrent(originalSnapshot)) {
          return Promise.reject(buildError('登录状态已变化，请重新登录', error))
        }

        // A same-session refresh may have completed while this 401 was in flight.
        if (!userStore.isCredentialsCurrent(originalSnapshot)) {
          const currentSnapshot = userStore.captureCredentials()
          if (!userStore.isSessionCurrent(originalSnapshot) || !currentSnapshot.token) {
            return Promise.reject(buildError('登录状态已变化，请重新登录', error))
          }
          originalConfig._retried = true
          originalConfig.headers ||= {}
          originalConfig.headers.Authorization = `Bearer ${currentSnapshot.token}`
          originalConfig._sessionSnapshot = currentSnapshot
          return api(originalConfig)
        }

        if (!originalSnapshot.refreshToken) {
          await expireSession(originalSnapshot, userStore)
          return Promise.reject(buildError('登录已过期，请重新登录', error))
        }

        originalConfig._retried = true
        const refreshedSnapshot = await refreshForSnapshot(originalSnapshot)

        if (refreshedSnapshot && userStore.isSessionCurrent(originalSnapshot) &&
            userStore.isCredentialsCurrent(refreshedSnapshot)) {
          originalConfig.headers ||= {}
          originalConfig.headers.Authorization = `Bearer ${refreshedSnapshot.token}`
          originalConfig._sessionSnapshot = refreshedSnapshot
          return api(originalConfig)
        }

        if (userStore.isSessionCurrent(originalSnapshot) &&
            !userStore.isCredentialsCurrent(originalSnapshot)) {
          return Promise.reject(buildError('登录状态已变化，请重新登录', error))
        }

        // Refresh failed: invalidate only the credentials that initiated it.
        await expireSession(originalSnapshot, userStore)
        return Promise.reject(buildError('登录已过期，请重新登录', error))
      }

      if (status === 403) {
        errorMessage = '没有权限执行此操作'
      } else if (status === 404) {
        errorMessage = '请求的资源不存在'
      } else if (status === 429) {
        errorMessage = error.response.data?.message || '请求过于频繁，请稍后再试'
      }
    } else {
      logError(`网络错误: ${method} ${url}`, error)
      errorMessage = '网络错误，请检查网络连接'
    }

    return Promise.reject(buildError(errorMessage, error))
  }
)

/**
 * 构造携带原始信息的 Error 对象。
 */
function buildError(message, original) {
  const customError = new Error(message)
  customError.config = original?.config
  customError.response = original?.response
  const responseData = original?.response?.data
  customError.errorCode = responseData?.error_code || responseData?.data?.error_code
  customError.requestId = responseData?.request_id || responseData?.data?.request_id
  customError.originalError = original
  return customError
}

export default api

/**
 * 认证相关 API
 */
export const authApi = {
  /** 登录 */
  login: (data) => api.post('/auth/login', data),
  /** 注册 */
  register: (data) => api.post('/auth/register', data),
  /** 获取当前用户信息 */
  getMe: () => api.get('/auth/me'),
  /** 登出 */
  logout: (credentials = {}) => api.post(
    '/auth/logout',
    credentials.refreshToken ? { refresh_token: credentials.refreshToken } : {},
    {
      skipAuthSession: true,
      headers: credentials.token ? { Authorization: `Bearer ${credentials.token}` } : {}
    }
  ),
  /** 刷新 Token */
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken })
}

/**
 * 文章相关 API
 */
export const articleApi = {
  /** 获取文章列表 */
  getList: (params) => api.get('/articles', { params }),
  /** 获取我的文章列表 */
  getMyList: (params) => api.get('/articles/my', { params }),
  /** 获取文章详情 */
  getDetail: (id, config) => config
    ? api.get(`/articles/${id}`, config)
    : api.get(`/articles/${id}`),
  /** 获取热门文章 */
  getHot: () => api.get('/articles/hot'),
  /** 获取文章分类 */
  getTypes: () => api.get('/articles/types'),
  /** 创建文章 */
  create: (data, config) => config
    ? api.post('/articles', data, config)
    : api.post('/articles', data),
  /** 更新文章 */
  update: (id, data, config) => config
    ? api.put(`/articles/${id}`, data, config)
    : api.put(`/articles/${id}`, data),
  /** 切换本人文章分类 */
  updateType: (id, type) => api.put(`/articles/${id}/type`, { type }),
  /** 删除文章 */
  delete: (id) => api.delete(`/articles/${id}`),
  /** 切换文章推荐状态 */
  toggleRecommend: (id) => api.post(`/articles/${id}/recommend`)
}

/**
 * 评论相关 API
 */
export const commentApi = {
  /** 获取文章评论 */
  getByArticle: (articleId, params) => api.get(`/comments/article/${articleId}`, { params }),
  /** 发表评论 */
  create: (data) => api.post('/comments', data),
  /** 删除评论 */
  delete: (id) => api.delete(`/comments/${id}`),
  /** 点赞评论（vote_type=1） */
  agree: (id) => api.post(`/comments/${id}/vote`, { vote_type: 1 }),
  /** 反对评论（vote_type=-1） */
  oppose: (id) => api.post(`/comments/${id}/vote`, { vote_type: -1 })
}

/**
 * 收藏相关 API
 */
export const favoriteApi = {
  /** 获取收藏列表 */
  getList: (params) => api.get('/favorites', { params }),
  /** 添加收藏 */
  add: (articleId) => api.post('/favorites', { articleid: articleId }),
  /** 取消收藏 */
  remove: (articleId) => api.delete(`/favorites/${articleId}`),
  /** 检查是否已收藏 */
  check: (articleId) => api.get(`/favorites/check/${articleId}`)
}

/**
 * 用户相关 API
 */
export const userApi = {
  /** 获取用户资料 */
  getProfile: (id) => api.get(`/users/${id}`),
  /** 更新个人资料 */
  updateProfile: (data, config) => config
    ? api.put('/users/profile', data, config)
    : api.put('/users/profile', data),
  /** 修改密码 */
  updatePassword: (data, config) => config
    ? api.post('/users/password', data, config)
    : api.post('/users/password', data)
}

/**
 * 文件上传 API
 */
export const uploadApi = {
  /** 上传图片 */
  uploadImage: (file, config) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/image', formData, {
      ...config,
      headers: { 'Content-Type': 'multipart/form-data', ...config?.headers }
    })
  },
  /** 上传文件 */
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  /** 上传头像 */
  uploadAvatar: (file, config) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/avatar', formData, {
      ...config,
      headers: { 'Content-Type': 'multipart/form-data', ...config?.headers }
    })
  }
}

/**
 * 积分相关 API
 */
export const creditApi = {
  /** 获取积分记录 */
  getList: (params) => api.get('/credits/history', { params }),
  /** 获取积分概况（余额） */
  getSummary: () => api.get('/credits/balance'),
  /** 支付文章积分 */
  payArticle: (articleId) => api.post(`/credits/pay-article/${articleId}`),
  /** 检查文章支付状态 */
  checkArticle: (articleId) => api.get(`/credits/check-article/${articleId}`)
}

/**
 * 管理员 API
 */
export const adminApi = {
  /** 获取统计数据 */
  getStats: () => api.get('/admin/stats'),
  /** 获取用户列表 */
  getUsers: (params) => api.get('/admin/users', { params }),
  /** 获取管理员文章列表 */
  getArticles: (params) => api.get('/admin/articles', { params }),
  /** 获取文章分类/菜单节点 */
  getArticleCategories: () => api.get('/admin/article-categories'),
  /** 创建文章分类/菜单节点 */
  createArticleCategory: (data) => api.post('/admin/article-categories', data),
  /** 更新文章分类/菜单节点 */
  updateArticleCategory: (id, data) => api.put(`/admin/article-categories/${id}`, data),
  /** 删除文章分类/菜单节点 */
  deleteArticleCategory: (id, params) => api.delete(`/admin/article-categories/${id}`, { params }),
  /** 管理员切换文章分类 */
  updateArticleType: (articleId, type) => api.put(`/admin/articles/${articleId}/type`, { type }),
  /** 切换文章隐藏状态 */
  toggleHide: (articleId) => api.post(`/articles/${articleId}/hide`),
  /** 切换文章审核状态 */
  toggleCheck: (articleId) => api.post(`/articles/${articleId}/check`),
  /** 切换文章推荐状态 */
  toggleRecommend: (articleId) => api.post(`/articles/${articleId}/recommend`)
}

/**
 * 我的评论 API
 */
export const myCommentApi = {
  /** 获取我的评论列表 */
  getMyComments: (params) => api.get('/comments/my', { params })
}

/**
 * 草稿箱 API
 */
export const draftApi = {
  /** 获取我的草稿列表 */
  getMyDrafts: (params) => api.get('/articles/drafts/my', { params })
}

/**
 * 系统监控 API
 */
export const systemApi = {
  /** 获取系统状态 */
  getStatus: () => api.get('/system/status'),
  /** 获取数据库状态 */
  getDatabase: () => api.get('/system/db'),
  /** 健康检查 */
  healthCheck: () => api.get('/system/health')
}

/**
 * 数学训练 API
 */
export const mathTrainingApi = {
  /** 创建训练记录 */
  createRecord: (data) => api.post('/math-training/records', data),
  /** 获取训练记录列表 */
  getRecords: (params) => api.get('/math-training/records', { params }),
  /** 获取训练记录详情 */
  getRecordDetail: (id) => api.get(`/math-training/records/${id}`),
  /** 获取错题列表 */
  getWrongAnswers: (params) => api.get('/math-training/wrong-answers', { params }),
  /** 获取训练统计摘要 */
  getSummary: () => api.get('/math-training/summary')
}
