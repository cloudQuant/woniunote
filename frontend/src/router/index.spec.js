import { describe, it, expect, beforeEach, vi } from 'vitest'

// Deterministic localStorage so the user store constructs cleanly.
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
// jsdom doesn't implement scrollTo; the router's scrollBehavior calls it.
vi.stubGlobal('scrollTo', () => {})

import { setActivePinia, createPinia } from 'pinia'
import router from './index'
import { useUserStore } from '@/stores/user'

/**
 * Exercises the route table + global beforeEach guard (auth/admin/guest
 * redirects and document.title side effect) using the real router instance.
 */
describe('router', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('defines the expected named routes', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).toContain('Home')
    expect(names).toContain('ArticleDetail')
    expect(names).toContain('Login')
    expect(names).toContain('AdminDashboard')
    expect(names).toContain('UserArticleCategories')
    expect(names).toContain('NotFound')
  })

  it('CategoryDefault redirects to Category page 1', async () => {
    await router.push('/type/5')
    expect(router.currentRoute.value.name).toBe('Category')
    expect(String(router.currentRoute.value.params.page)).toBe('1')
    expect(String(router.currentRoute.value.params.type)).toBe('5')
  })

  it('redirects anonymous users away from auth-required routes', async () => {
    await router.push('/write')
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query.redirect).toBe('/write')
  })

  it('redirects non-admins away from admin routes to Home', async () => {
    const store = useUserStore()
    store.token = 'tok'
    store.user = { userid: 1, role: 'user' }
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Home')
  })

  it('allows admins into admin routes', async () => {
    const store = useUserStore()
    store.token = 'tok'
    store.user = { userid: 1, role: 'admin' }
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('AdminDashboard')
  })

  it('allows regular users into personal-center article category management', async () => {
    const store = useUserStore()
    store.token = 'tok'
    store.user = { userid: 1, role: 'user' }
    await router.push('/user/categories')
    expect(router.currentRoute.value.name).toBe('UserArticleCategories')
  })

  it('redirects logged-in users away from guest-only pages', async () => {
    const store = useUserStore()
    store.token = 'tok'
    store.user = { userid: 1, role: 'user' }
    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('Home')
  })

  it('sets document.title from route meta', async () => {
    await router.push('/login') // guest page, anonymous → stays
    await router.isReady()
    expect(document.title).toContain('cloudQuant')
  })

  it('allows anonymous access to public pages', async () => {
    await router.push('/search')
    expect(router.currentRoute.value.name).toBe('Search')
  })
})
