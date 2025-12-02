import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'
import { logInfo, logError, logWarning, logRequest } from '@/utils/logger'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
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

// 响应拦截器
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

// 认证API
export const authApi = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken })
}

// 文章API
export const articleApi = {
  getList: (params) => api.get('/articles/', { params }),
  getMyList: (params) => api.get('/articles/my', { params }),
  getDetail: (id) => api.get(`/articles/${id}`),
  getHot: () => api.get('/articles/hot'),
  getTypes: () => api.get('/articles/types'),
  create: (data) => api.post('/articles/', data),
  update: (id, data) => api.put(`/articles/${id}`, data),
  delete: (id) => api.delete(`/articles/${id}`),
  toggleRecommend: (id) => api.post(`/articles/${id}/recommend`)
}

// 评论API
export const commentApi = {
  getByArticle: (articleId, params) => api.get(`/comments/article/${articleId}`, { params }),
  create: (data) => api.post('/comments/', data),
  update: (id, data) => api.put(`/comments/${id}`, data),
  delete: (id) => api.delete(`/comments/${id}`),
  agree: (id) => api.post(`/comments/${id}/agree`),
  oppose: (id) => api.post(`/comments/${id}/oppose`)
}

// 收藏API
export const favoriteApi = {
  getList: (params) => api.get('/favorites/', { params }),
  add: (articleId) => api.post('/favorites/', { articleid: articleId }),
  remove: (articleId) => api.delete(`/favorites/${articleId}`),
  check: (articleId) => api.get(`/favorites/check/${articleId}`)
}

// 用户API
export const userApi = {
  getProfile: (id) => api.get(`/users/${id}`),
  updateProfile: (data) => api.put('/users/me', data),
  updatePassword: (data) => api.put('/users/me/password', data)
}

// 上传API
export const uploadApi = {
  uploadImage: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadAvatar: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

// 积分API
export const creditApi = {
  getList: (params) => api.get('/credits/', { params }),
  getSummary: () => api.get('/credits/summary'),
  payArticle: (articleId) => api.post(`/credits/pay-article/${articleId}`),
  checkArticle: (articleId) => api.get(`/credits/check-article/${articleId}`)
}

// 管理员API
export const adminApi = {
  getStats: () => api.get('/admin/stats'),
  getUsers: (params) => api.get('/admin/users', { params }),
  toggleHide: (articleId) => api.post(`/articles/${articleId}/hide`),
  toggleCheck: (articleId) => api.post(`/articles/${articleId}/check`),
  toggleRecommend: (articleId) => api.post(`/articles/${articleId}/recommend`)
}

// 扩展评论API
export const myCommentApi = {
  getMyComments: (params) => api.get('/comments/my', { params })
}

// 草稿API
export const draftApi = {
  getMyDrafts: (params) => api.get('/articles/drafts/my', { params })
}

// 待办事项API
export const todoApi = {
  // 分类
  getCategories: () => api.get('/todos/categories'),
  createCategory: (data) => api.post('/todos/categories', data),
  updateCategory: (id, data) => api.put(`/todos/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/todos/categories/${id}`),
  // 事项
  getItems: (params) => api.get('/todos/items', { params }),
  createItem: (data) => api.post('/todos/items', data),
  updateItem: (id, data) => api.put(`/todos/items/${id}`, data),
  toggleItem: (id) => api.post(`/todos/items/${id}/toggle`),
  deleteItem: (id) => api.delete(`/todos/items/${id}`),
  getStats: () => api.get('/todos/stats')
}

// 卡片管理API
export const cardApi = {
  // 分类
  getCategories: () => api.get('/cards/categories'),
  createCategory: (data) => api.post('/cards/categories', data),
  updateCategory: (id, data) => api.put(`/cards/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/cards/categories/${id}`),
  // 卡片
  getCards: (params) => api.get('/cards/', { params }),
  getCard: (id) => api.get(`/cards/${id}`),
  createCard: (data) => api.post('/cards/', data),
  updateCard: (id, data) => api.put(`/cards/${id}`, data),
  deleteCard: (id) => api.delete(`/cards/${id}`),
  // 时间追踪
  startCard: (id) => api.post(`/cards/${id}/start`),
  stopCard: (id) => api.post(`/cards/${id}/stop`),
  completeCard: (id) => api.post(`/cards/${id}/complete`),
  reopenCard: (id) => api.post(`/cards/${id}/reopen`),
  getStats: () => api.get('/cards/stats/summary')
}

// 系统监控API
export const systemApi = {
  getStatus: () => api.get('/system/status'),
  getDatabase: () => api.get('/system/database'),
  healthCheck: () => api.get('/system/health')
}
