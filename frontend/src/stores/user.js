/**
 * @module stores/user
 * @description 用户状态管理 Store
 * 管理用户登录状态、Token、用户信息以及权限判断。
 */

import { defineStore } from 'pinia'
import { computed, onScopeDispose, ref } from 'vue'
import { authApi } from '@/api'
import { authSessionStorage } from '@/utils/authSessionStorage'
import { notifyError } from '@/utils/errorToast'
import { logWarning } from '@/utils/logger'

const SESSION_STATE_KEY = 'woniunote:auth-session'
const SESSION_LOCK_NAME = 'woniunote:auth-session-lock'

let storageListenerInstalled = false
let activeSessionSync = null

function makeSessionMarker() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function getUserIdentity(user) {
  if (user?.userid !== undefined && user?.userid !== null) return `id:${user.userid}`
  if (user?.id !== undefined && user?.id !== null) return `id:${user.id}`
  if (user?.username) return `name:${user.username}`
  return null
}

function getRecoveryOwnerId(user) {
  return user?.userid ?? user?.id ?? user?.username ?? null
}

async function withSessionLock(callback) {
  if (typeof navigator !== 'undefined' && navigator.locks?.request) {
    return navigator.locks.request(SESSION_LOCK_NAME, callback)
  }
  // IndexedDB transactions remain the cross-tab compare-and-update authority
  // when the optional Web Locks API is unavailable.
  return callback()
}

function installStorageListener() {
  if (storageListenerInstalled || typeof window === 'undefined') return
  storageListenerInstalled = true
  window.addEventListener('storage', (event) => {
    if (event.key !== SESSION_STATE_KEY || !activeSessionSync) return
    activeSessionSync().catch((error) => {
      logWarning('跨标签会话同步失败', { message: error?.message || '未知错误' })
    })
  })
}

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const refreshToken = ref('')
  const user = ref(null)
  const sessionGeneration = ref(0)
  let currentEpoch = ''
  let currentVersion = ''
  let highestSeenRevision = -1
  let pendingLogoutEpoch = null
  let sessionStorageAvailable = true

  function reconcile(shared) {
    if (!shared?.epoch || !shared?.version || !Number.isSafeInteger(shared.revision) ||
        shared.revision < 0) {
      throw new Error('安全登录会话记录版本无效')
    }
    if (shared.revision < highestSeenRevision) return false
    // Logout revokes the active epoch locally before its durable tombstone is
    // committed. Reads of that same epoch during the wait must not rehydrate
    // credentials, even though they carry the last committed revision.
    if (pendingLogoutEpoch && shared.epoch === pendingLogoutEpoch) return false
    if (shared.revision === highestSeenRevision) {
      const sameRecord = shared.epoch === currentEpoch && shared.version === currentVersion &&
        shared.token === token.value && shared.refreshToken === refreshToken.value &&
        JSON.stringify(shared.user) === JSON.stringify(user.value)
      if (!sameRecord) {
        throw new Error('安全登录会话版本冲突，已阻止旧状态覆盖')
      }
      return true
    }
    if (shared.epoch !== currentEpoch && currentEpoch) sessionGeneration.value += 1

    currentEpoch = shared.epoch
    currentVersion = shared.version
    highestSeenRevision = shared.revision
    if (pendingLogoutEpoch && shared.epoch !== pendingLogoutEpoch) pendingLogoutEpoch = null
    token.value = shared.token
    refreshToken.value = shared.refreshToken
    user.value = shared.user ? { ...shared.user } : null
    return true
  }

  function failClosed(error) {
    if (!sessionStorageAvailable) return
    sessionStorageAvailable = false
    sessionGeneration.value += 1
    currentEpoch = ''
    currentVersion = ''
    token.value = ''
    refreshToken.value = ''
    user.value = null
    logWarning('安全登录会话存储不可用，已清除内存登录状态', {
      message: error?.message || '未知错误'
    })
    notifyError(error, '安全登录会话存储不可用，无法恢复登录状态')
  }

  const sessionReadyPromise = authSessionStorage.readCurrent()
    .then((shared) => {
      reconcile(shared)
      return true
    })
    .catch((error) => {
      failClosed(error)
      return false
    })

  async function ensureSessionReady() {
    const ready = await sessionReadyPromise
    if (!ready || !sessionStorageAvailable) {
      throw new Error('安全登录会话存储不可用，请刷新页面后重试')
    }
  }

  async function syncSession() {
    await ensureSessionReady()
    try {
      const shared = await authSessionStorage.readCurrent()
      sessionStorageAvailable = true
      reconcile(shared)
      return captureCredentials()
    } catch (error) {
      failClosed(error)
      throw error
    }
  }

  activeSessionSync = syncSession
  installStorageListener()
  onScopeDispose(() => {
    if (activeSessionSync === syncSession) activeSessionSync = null
  })

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role))

  function captureCredentials() {
    return {
      generation: sessionGeneration.value,
      epoch: currentEpoch,
      version: currentVersion,
      token: token.value,
      refreshToken: refreshToken.value,
      userIdentity: getUserIdentity(user.value),
      userId: getRecoveryOwnerId(user.value)
    }
  }

  function isSessionCurrent(snapshot) {
    return !!snapshot && snapshot.generation === sessionGeneration.value &&
      snapshot.epoch === currentEpoch && snapshot.userIdentity === getUserIdentity(user.value)
  }

  function isCredentialsCurrent(snapshot) {
    return isSessionCurrent(snapshot) && snapshot.token === token.value &&
      snapshot.refreshToken === refreshToken.value
  }

  function isSameSession(shared, snapshot) {
    return !!snapshot && shared.epoch === snapshot.epoch &&
      getUserIdentity(shared.user) === snapshot.userIdentity
  }

  function isSameCredentials(shared, snapshot) {
    return isSameSession(shared, snapshot) && shared.token === snapshot.token &&
      shared.refreshToken === snapshot.refreshToken
  }

  function makeLoggedOutSession() {
    return {
      epoch: makeSessionMarker(),
      version: makeSessionMarker(),
      token: '',
      refreshToken: '',
      user: null
    }
  }

  function mirrorSession(shared) {
    try {
      localStorage.setItem(SESSION_STATE_KEY, JSON.stringify(shared))
      if (shared.token) localStorage.setItem('token', shared.token)
      else localStorage.removeItem('token')
      if (shared.refreshToken) localStorage.setItem('refreshToken', shared.refreshToken)
      else localStorage.removeItem('refreshToken')
      if (shared.user) localStorage.setItem('user', JSON.stringify(shared.user))
      else localStorage.removeItem('user')
      localStorage.setItem('woniunote:auth-session-epoch', shared.epoch)
      localStorage.setItem('woniunote:auth-session-version', shared.version)
    } catch (error) {
      // IndexedDB already committed; legacy mirrors only notify other tabs and
      // support older code paths, so their failure cannot roll back authority.
      logWarning('安全登录会话已保存，但兼容镜像更新失败', {
        message: error?.message || '未知错误'
      })
    }
  }

  async function commitSession(update) {
    await ensureSessionReady()
    try {
      return await withSessionLock(async () => {
        const transaction = await authSessionStorage.transact(update)
        reconcile(transaction.session)
        if (transaction.committed) mirrorSession(transaction.session)
        return transaction
      })
    } catch (error) {
      failClosed(error)
      throw error
    }
  }

  async function login(username, password, captchaId = null, captchaCode = null) {
    await syncSession()
    const current = captureCredentials()
    const loginGeneration = ++sessionGeneration.value
    const loginData = { username, password }
    if (captchaId && captchaCode) {
      loginData.captcha_id = captchaId
      loginData.captcha_code = captchaCode
    }

    const res = await authApi.login(loginData)
    const transaction = await commitSession((shared) => {
      if (loginGeneration !== sessionGeneration.value || shared.epoch !== current.epoch ||
          shared.version !== current.version) return { result: false }

      return {
        session: {
          epoch: makeSessionMarker(),
          version: makeSessionMarker(),
          token: res.data.access_token || '',
          refreshToken: res.data.refresh_token || '',
          user: res.data.user || null
        },
        result: true
      }
    })
    if (!transaction.result) throw new Error('登录状态已变化，请重新登录')
    return res
  }

  /** 用户注册；未知提交结果由调用方提示核实，不自动重发。 */
  async function register(userData) {
    return authApi.register(userData)
  }

  /** 仅清理当前会话；要求请求开始时的完整凭据仍是权威记录。 */
  async function clearSession(expectedSnapshot = null) {
    const transaction = await commitSession((shared) => {
      if (expectedSnapshot && (expectedSnapshot.generation !== sessionGeneration.value ||
          !isSameCredentials(shared, expectedSnapshot))) return { result: false }
      return { session: makeLoggedOutSession(), result: true }
    })
    return transaction.result
  }

  /** 主动退出忽略同 epoch 内的令牌轮换，但保留之后的新登录。 */
  async function clearSessionForLogout(snapshot) {
    const transaction = await commitSession((shared) => {
      if (!isSameSession(shared, snapshot)) return { result: false }
      return { session: makeLoggedOutSession(), result: true }
    })
    return transaction.result
  }

  /** 主动退出先使本地代际失效，再用捕获的凭据请求服务端撤销。 */
  async function logout() {
    const credentials = captureCredentials()
    const hasCredentials = !!(credentials.token || credentials.refreshToken)

    sessionGeneration.value += 1
    pendingLogoutEpoch = hasCredentials ? credentials.epoch : null
    token.value = ''
    refreshToken.value = ''
    user.value = null

    if (!hasCredentials) {
      try {
        await ensureSessionReady()
      } catch (error) {
        return { revoked: false, error }
      }
      return { revoked: true }
    }

    let localClearError = null
    try {
      await ensureSessionReady()
      await clearSessionForLogout(credentials)
    } catch (error) {
      localClearError = error
    }

    try {
      await authApi.logout(credentials)
      return localClearError
        ? { revoked: false, error: localClearError }
        : { revoked: true }
    } catch (error) {
      return { revoked: false, error: localClearError || error }
    }
  }

  /** 获取本人的最新资料；只允许同一代、同一身份的结果写回。 */
  async function refreshUserInfo() {
    await syncSession()
    const snapshot = captureCredentials()
    if (!snapshot.token) return

    let response
    try {
      response = await authApi.getMe()
    } catch (error) {
      try {
        if (await clearSession(snapshot)) {
          notifyError(error, '刷新用户信息失败，本地登录状态已清除')
        }
      } catch (storageError) {
        notifyError(storageError, '无法确认登录状态，请刷新页面后重试')
      }
      return
    }
    await updateUser(response.data, snapshot)
  }

  async function updateUser(userData, expectedSnapshot = null) {
    await syncSession()
    const snapshot = expectedSnapshot || captureCredentials()
    const transaction = await commitSession((shared) => {
      if ((snapshot.generation !== sessionGeneration.value && expectedSnapshot) ||
          !isSameSession(shared, snapshot)) return { result: false }

      return {
        session: {
          ...shared,
          version: makeSessionMarker(),
          user: { ...shared.user, ...userData }
        },
        result: true
      }
    })
    return transaction.result
  }

  /** 更新当前会话令牌；较早的refresh结果不能覆盖已变化的凭据。 */
  async function setTokens(accessToken, newRefreshToken, expectedSnapshot = null) {
    await syncSession()
    const snapshot = expectedSnapshot || captureCredentials()
    const transaction = await commitSession((shared) => {
      if ((expectedSnapshot && snapshot.generation !== sessionGeneration.value) ||
          (expectedSnapshot && !isSameCredentials(shared, snapshot))) return { result: false }

      return {
        session: {
          ...shared,
          version: makeSessionMarker(),
          token: accessToken || '',
          refreshToken: newRefreshToken || shared.refreshToken
        },
        result: true
      }
    })
    return transaction.result
  }

  return {
    token,
    refreshToken,
    user,
    sessionGeneration,
    isLoggedIn,
    isAdmin,
    isEditor,
    ensureSessionReady,
    syncSession,
    captureCredentials,
    isSessionCurrent,
    isCredentialsCurrent,
    login,
    register,
    clearSession,
    clearSessionForLogout,
    logout,
    refreshUserInfo,
    updateUser,
    setTokens
  }
})
