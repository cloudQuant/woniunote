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

vi.mock('@/utils/authSessionStorage', async () => {
  const { authSessionStorageMock } = await import('@/test/authSessionStorageMock')
  return { authSessionStorage: authSessionStorageMock }
})
import { authSessionStorageMock } from '@/test/authSessionStorageMock'

// Every lazy view chunk imports Element Plus at module scope. Loading the real
// library in jsdom costs seconds and made the lazy-route navigation test flake
// once api/index.js stopped importing it eagerly (Epic 18.1). This spec only
// exercises the route table and guards, so mock it like the view specs do;
// toast behaviour is asserted in the view/errorToast specs.
vi.mock('element-plus', () => {
  const elMessage = Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  })
  return {
    default: {},
    ElMessage: elMessage,
    ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) },
    ElConfigProvider: { name: 'ElConfigProvider', render: () => null }
  }
})

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
    authSessionStorageMock.reset()
  })

  function seedSession(user = null) {
    authSessionStorageMock.setCurrent({
      epoch: 'router-test-epoch',
      version: 'router-test-version',
      revision: 0,
      token: user ? 'tok' : '',
      refreshToken: user ? 'refresh' : '',
      user
    })
  }

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
    seedSession({ userid: 1, role: 'user' })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Home')
  })

  it('allows admins into admin routes', async () => {
    seedSession({ userid: 1, role: 'admin' })
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('AdminDashboard')
  })

  it('allows regular users into personal-center article category management', async () => {
    seedSession({ userid: 1, role: 'user' })
    await router.push('/user/categories')
    expect(router.currentRoute.value.name).toBe('UserArticleCategories')
  })

  it('opens the personal category route on the maintenance tab', () => {
    const record = router.resolve('/user/categories').matched.at(-1)
    expect(record.props.default).toEqual({ initialTab: 'categories' })
  })

  it('redirects logged-in users away from guest-only pages', async () => {
    seedSession({ userid: 1, role: 'user' })
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

  it('waits for the authoritative session read before guarding a hard-refresh route', async () => {
    seedSession({ userid: 1, role: 'user' })
    const read = authSessionStorageMock.deferNextRead()
    let navigationSettled = false
    const navigation = router.push('/user/categories').finally(() => {
      navigationSettled = true
    })
    await read.started

    expect(navigationSettled).toBe(false)
    read.release()
    await navigation
    expect(router.currentRoute.value.name).toBe('UserArticleCategories')
    expect(useUserStore().isLoggedIn).toBe(true)
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
