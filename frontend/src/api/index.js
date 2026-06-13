/**
 * @module api
 * @description 全局 API 接口封装模块
 * 包含 Axios 实例配置、拦截器处理以及各个业务模块的 API 定义。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'
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

// ---- Token 无感刷新状态 ----
// 当多个请求同时收到 401 时，只发起一次 refresh，其余请求排队等待新 token。
let isRefreshing = false
let refreshSubscribers = []

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken) {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

function onRefreshFailed() {
  refreshSubscribers.forEach((cb) => cb(null))
  refreshSubscribers = []
}

/**
 * 用 refresh_token 静默换取新的 access_token。
 * 直接用裸 axios，避免触发本实例拦截器导致递归。
 * @returns {Promise<string|null>} 新 access token，失败返回 null
 */
async function refreshAccessToken() {
  const userStore = useUserStore()
  const rt = userStore.refreshToken
  if (!rt) return null
  try {
    const resp = await axios.post('/api/auth/refresh', { refresh_token: rt })
    const data = resp.data
    if (data?.code === 200 && data.data?.access_token) {
      userStore.setTokens(data.data.access_token, data.data.refresh_token)
      return data.data.access_token
    }
    return null
  } catch {
    return null
  }
}

/**
 * 请求拦截器
 * 处理 Token 注入和请求日志记录
 */
api.interceptors.request.use(
  config => {
    // 记录请求开始时间
    config.metadata = { startTime: Date.now() }

    // 全局 loading（除非显式跳过，如静默刷新/轮询）
    if (!config.skipLoading) {
      startLoading()
      config._loadingStarted = true
    }

    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }

    logInfo(`API请求开始: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  error => {
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
    if (response.config?._loadingStarted) stopLoading()

    // 计算请求耗时
    const duration = Date.now() - (response.config.metadata?.startTime || Date.now())
    const method = response.config.method?.toUpperCase()
    const url = response.config.url

    logRequest(method, url, response.status, duration)

    const data = response.data
    if (data.code !== 200) {
      logWarning(`API响应异常: ${method} ${url}`, { code: data.code, message: data.message })
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  async error => {
    if (error.config?._loadingStarted) stopLoading()

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
      const isAuthEndpoint = url?.includes('/auth/login') ||
                             url?.includes('/auth/register') ||
                             url?.includes('/auth/refresh')

      // 401：尝试用 refresh_token 无感刷新并重放原请求（每个请求只重试一次）
      if (status === 401 && !isAuthEndpoint && !originalConfig._retried) {
        const userStore = useUserStore()
        if (!userStore.refreshToken) {
          userStore.logout()
          router.push({ name: 'Login' })
          return Promise.reject(buildError('登录已过期，请重新登录', error))
        }

        originalConfig._retried = true

        if (isRefreshing) {
          // 已有刷新在进行：排队等待新 token
          return new Promise((resolve, reject) => {
            subscribeTokenRefresh((newToken) => {
              if (!newToken) {
                reject(buildError('登录已过期，请重新登录', error))
                return
              }
              originalConfig.headers.Authorization = `Bearer ${newToken}`
              resolve(api(originalConfig))
            })
          })
        }

        isRefreshing = true
        const newToken = await refreshAccessToken()
        isRefreshing = false

        if (newToken) {
          onTokenRefreshed(newToken)
          originalConfig.headers.Authorization = `Bearer ${newToken}`
          return api(originalConfig)
        }

        // 刷新失败：清理队列并登出
        onRefreshFailed()
        userStore.logout()
        router.push({ name: 'Login' })
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
  customError.response = original?.response
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
  logout: () => api.post('/auth/logout'),
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
  getDetail: (id) => api.get(`/articles/${id}`),
  /** 获取热门文章 */
  getHot: () => api.get('/articles/hot'),
  /** 获取文章分类 */
  getTypes: () => api.get('/articles/types'),
  /** 创建文章 */
  create: (data) => api.post('/articles', data),
  /** 更新文章 */
  update: (id, data) => api.put(`/articles/${id}`, data),
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
  updateProfile: (data) => api.put('/users/profile', data),
  /** 修改密码 */
  updatePassword: (data) => api.post('/users/password', data)
}

/**
 * 文件上传 API
 */
export const uploadApi = {
  /** 上传图片 */
  uploadImage: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
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
  uploadAvatar: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
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
