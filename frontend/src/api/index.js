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

/**
 * 请求拦截器
 * 处理 Token 注入和请求日志记录
 */
api.interceptors.request.use(
  config => {
    // 记录请求开始时间
    config.metadata = { startTime: Date.now() }
    
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
 * 处理响应日志、错误统一处理和 Token 过期跳转
 */
api.interceptors.response.use(
  response => {
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
  error => {
    // 计算请求耗时
    const duration = Date.now() - (error.config?.metadata?.startTime || Date.now())
    const method = error.config?.method?.toUpperCase()
    const url = error.config?.url
    
    let errorMessage = '请求失败'
    
    if (error.response) {
      const status = error.response.status
      errorMessage = error.response.data?.detail || error.response.data?.message || '请求失败'
      
      logRequest(method, url, status, duration)
      
      if (status === 401 && !url?.includes('/auth/login')) {
        const userStore = useUserStore()
        userStore.logout()
        router.push({ name: 'Login' })
        errorMessage = '登录已过期，请重新登录'
      } else if (status === 403) {
        errorMessage = '没有权限执行此操作'
      } else if (status === 404) {
        errorMessage = '请求的资源不存在'
      }
    } else {
      logError(`网络错误: ${method} ${url}`, error)
      errorMessage = '网络错误，请检查网络连接'
    }
    
    // 创建带有明确错误信息的Error对象
    const customError = new Error(errorMessage)
    customError.response = error.response
    customError.originalError = error
    
    return Promise.reject(customError)
  }
)

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
  /** 更新评论 */
  update: (id, data) => api.put(`/comments/${id}`, data),
  /** 删除评论 */
  delete: (id) => api.delete(`/comments/${id}`),
  /** 点赞评论 */
  agree: (id) => api.post(`/comments/${id}/agree`),
  /** 反对评论 */
  oppose: (id) => api.post(`/comments/${id}/oppose`)
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
  updateProfile: (data) => api.put('/users/me', data),
  /** 修改密码 */
  updatePassword: (data) => api.put('/users/me/password', data)
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
  getList: (params) => api.get('/credits', { params }),
  /** 获取积分概况 */
  getSummary: () => api.get('/credits/summary'),
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
  getDatabase: () => api.get('/system/database'),
  /** 获取实时指标 */
  getMetrics: () => api.get('/system/metrics'),
  /** 获取进程列表 */
  getProcesses: (limit = 10) => api.get(`/system/processes?limit=${limit}`),
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
