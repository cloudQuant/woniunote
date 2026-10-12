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

  it('opens the personal category route on the maintenance tab', () => {
    const record = router.resolve('/user/categories').matched.at(-1)
    expect(record.props.default).toEqual({ initialTab: 'categories' })
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

  it('every lazy route chunk resolves to a component module', async () => {
    const records = router.getRoutes().filter((record) => record.components?.default)
    // The table is fully code-split; guard against a silently dropped loader.
    expect(records.length).toBeGreaterThanOrEqual(19)
    for (const record of records) {
      const component = record.components.default
      if (typeof component === 'function') {
        await expect(component()).resolves.toBeTruthy()
      } else {
        // vue-router caches the resolved module in place once a route has been
        // visited, so earlier navigations already exercised that loader.
        expect(component).toBeTruthy()
      }
    }
  })

  it('scrollBehavior restores the saved position, otherwise scrolls to top', () => {
    const scrollBehavior = router.options.scrollBehavior
    expect(scrollBehavior({}, {}, { top: 120, left: 0 })).toEqual({ top: 120, left: 0 })
    expect(scrollBehavior({}, {}, null)).toEqual({ top: 0 })
  })

  it('falls back to the bare app title for routes without meta.title', async () => {
    // Guard branch: `to.meta.title` falsy → plain 'cloudQuant'. The shipped
    // table gives every route a title, so register a title-less route here.
    router.addRoute({
      path: '/__untitled',
      name: '__Untitled',
      component: { render: () => null }
    })
    await router.push('/__untitled')
    expect(router.currentRoute.value.name).toBe('__Untitled')
    expect(document.title).toBe('cloudQuant')
  })
})
