/**
 * @module stores/user
 * @description 用户状态管理 Store
 * 管理用户登录状态、Token、用户信息以及权限判断。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  /**
   * 访问令牌
   * @type {import('vue').Ref<string>}
   */
  const token = ref(localStorage.getItem('token') || '')

  /**
   * 刷新令牌
   * @type {import('vue').Ref<string>}
   */
  const refreshToken = ref(localStorage.getItem('refreshToken') || '')

  /**
   * 用户信息对象
   * @type {import('vue').Ref<Object|null>}
   */
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // 计算属性
  /**
   * 是否已登录
   * @type {import('vue').ComputedRef<boolean>}
   */
  const isLoggedIn = computed(() => !!token.value && !!user.value)

  /**
   * 是否为管理员
   * @type {import('vue').ComputedRef<boolean>}
   */
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * 是否为编辑或管理员
   * @type {import('vue').ComputedRef<boolean>}
   */
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role))

  // Actions

  /**
   * 用户登录
   * 
   * @param {string} username - 用户名
   * @param {string} password - 密码
   * @param {string} [captchaId=null] - 验证码ID
   * @param {string} [captchaCode=null] - 验证码内容
   * @returns {Promise<Object>} 登录响应
   */
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

  /**
   * 用户注册
   * 
   * @param {Object} userData - 注册信息
   * @returns {Promise<Object>} 注册响应
   */
  async function register(userData) {
    const res = await authApi.register(userData)
    return res
  }

  /**
   * 用户登出
   * 清除状态和 localStorage
   */
  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null

    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  /**
   * 刷新用户信息
   * 从服务器重新获取最新用户信息
   */
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

  /**
   * 更新本地用户信息
   * 
   * @param {Object} userData - 新的用户信息片段
   */
  function updateUser(userData) {
    user.value = { ...user.value, ...userData }
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  /**
   * 更新访问/刷新令牌（用于无感刷新）。
   *
   * @param {string} accessToken - 新的访问令牌
   * @param {string} [newRefreshToken] - 新的刷新令牌（可选，后端轮换时提供）
   */
  function setTokens(accessToken, newRefreshToken) {
    token.value = accessToken || ''
    localStorage.setItem('token', token.value)
    if (newRefreshToken) {
      refreshToken.value = newRefreshToken
      localStorage.setItem('refreshToken', newRefreshToken)
    }
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
    updateUser,
    setTokens
  }
})
