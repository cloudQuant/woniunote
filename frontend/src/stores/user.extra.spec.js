import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const memoryStore = (() => {
  let data = {}
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v) },
    removeItem: (k) => { delete data[k] },
    clear: () => { data = {} }
  }
})()
vi.stubGlobal('localStorage', memoryStore)

vi.mock('@/utils/authSessionStorage', async () => {
  const { authSessionStorageMock } = await import('@/test/authSessionStorageMock')
  return { authSessionStorage: authSessionStorageMock }
})
import { authSessionStorageMock } from '@/test/authSessionStorageMock'

const api = vi.hoisted(() => ({
  getMe: vi.fn(),
  notifyError: vi.fn(),
  register: vi.fn(() => Promise.resolve({ data: { userid: 9 } })),
  login: vi.fn(() => Promise.resolve({
    data: { access_token: 'a', refresh_token: 'r', user: { userid: 1, role: 'editor' } }
  }))
}))
const { getMe, register } = api
vi.mock('@/api', () => ({
  authApi: { login: api.login, register: api.register, getMe: api.getMe }
}))
vi.mock('@/utils/errorToast', () => ({ notifyError: api.notifyError }))

import { useUserStore } from './user'

describe('user store — extra branches', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    authSessionStorageMock.reset()
    vi.clearAllMocks()
  })

  it('register delegates to authApi.register', async () => {
    const store = useUserStore()
    const res = await store.register({ username: 'x', password: 'y' })
    expect(register).toHaveBeenCalledWith({ username: 'x', password: 'y' })
    expect(res.data.userid).toBe(9)
  })

  it('isEditor true for editor and admin roles', async () => {
    const store = useUserStore()
    await store.login('x', 'y')
    expect(store.isEditor).toBe(true)
  })

  it('refreshUserInfo returns early when no token', async () => {
    const store = useUserStore()
    await store.refreshUserInfo()
    expect(getMe).not.toHaveBeenCalled()
  })

  it('refreshUserInfo logs out on API failure', async () => {
    const store = useUserStore()
    await store.login('x', 'y')
    const error = new Error('401')
    getMe.mockRejectedValueOnce(error)
    await store.refreshUserInfo()
    expect(store.token).toBe('')
    expect(store.user).toBe(null)
    expect(api.notifyError).toHaveBeenCalledWith(
      error,
      '刷新用户信息失败，本地登录状态已清除'
    )
  })

  it('updateUser merges into existing user and persists', async () => {
    const store = useUserStore()
    await store.login('x', 'y')
    await store.updateUser({ nickname: 'newname' })
    expect(store.user.nickname).toBe('newname')
    expect(store.user.role).toBe('editor')
    expect(JSON.parse(localStorage.getItem('user')).nickname).toBe('newname')
  })

  it('setTokens with empty access token clears it', async () => {
    const store = useUserStore()
    await store.login('x', 'y')
    await store.setTokens('')
    expect(store.token).toBe('')
  })
})
