import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// jsdom in some environments lacks a full localStorage; provide a stub so the
// store's persistence calls work deterministically under test.
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

// Mock API + logger so the store works without network.
vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(() => Promise.resolve({
      data: {
        access_token: 'access-1',
        refresh_token: 'refresh-1',
        user: { userid: 1, nickname: 'tester', role: 'user' }
      }
    })),
    register: vi.fn(() => Promise.resolve({ data: { userid: 1 } })),
    getMe: vi.fn(() => Promise.resolve({ data: { userid: 1, nickname: 'tester', role: 'admin' } }))
  }
}))

import { useUserStore } from './user'

describe('user store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('starts logged out', () => {
    const store = useUserStore()
    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('login stores tokens and user, persists to localStorage', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    expect(store.token).toBe('access-1')
    expect(store.refreshToken).toBe('refresh-1')
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('token')).toBe('access-1')
    expect(JSON.parse(localStorage.getItem('user')).nickname).toBe('tester')
  })

  it('setTokens updates access token and optional refresh token', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    store.setTokens('access-2')
    expect(store.token).toBe('access-2')
    // refresh token unchanged when not provided
    expect(store.refreshToken).toBe('refresh-1')
    store.setTokens('access-3', 'refresh-3')
    expect(store.refreshToken).toBe('refresh-3')
    expect(localStorage.getItem('refreshToken')).toBe('refresh-3')
  })

  it('logout clears state and storage', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBe(null)
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBe(null)
  })

  it('isAdmin reflects role', async () => {
    const store = useUserStore()
    await store.login('tester', 'pw', 'cid', 'CODE')
    expect(store.isAdmin).toBe(false)
    await store.refreshUserInfo()
    expect(store.isAdmin).toBe(true)
  })
})
