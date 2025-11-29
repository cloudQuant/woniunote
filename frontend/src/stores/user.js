import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const refreshToken = ref(localStorage.getItem('refreshToken') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role))

  // 登录
  async function login(username, password, captchaId = null, captchaCode = null) {
    const loginData = { username, password }
    if (captchaId && captchaCode) {
      loginData.captcha_id = captchaId
      loginData.captcha_code = captchaCode
    }
    
    const res = await authApi.login(loginData)
    token.value = res.data.access_token
    refreshToken.value = res.data.refresh_token
    user.value = res.data.user
    
    localStorage.setItem('token', token.value)
    localStorage.setItem('refreshToken', refreshToken.value)
    localStorage.setItem('user', JSON.stringify(user.value))
    
    return res
  }

  // 注册
  async function register(userData) {
    const res = await authApi.register(userData)
    return res
  }

  // 登出
  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  // 刷新用户信息
  async function refreshUserInfo() {
    if (!token.value) return
    
    try {
      const res = await authApi.getMe()
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(user.value))
    } catch (error) {
      logout()
    }
  }

  // 更新用户信息
  function updateUser(userData) {
    user.value = { ...user.value, ...userData }
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    isAdmin,
    isEditor,
    login,
    register,
    logout,
    refreshUserInfo,
    updateUser
  }
})
