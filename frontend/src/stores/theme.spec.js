import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import fc from 'fast-check'

// jsdom localStorage stub for deterministic persistence tests.
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

import { useThemeStore, applyThemeToDom } from './theme'
import { DEFAULT_THEME, THEME_STORAGE_KEY, THEME_KEYS, getThemeMeta } from '@/config/themes'

describe('theme store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    // reset DOM attributes between tests
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.classList.remove('dark')
  })

  it('defaults to the configured default theme', () => {
    const store = useThemeStore()
    expect(store.currentTheme).toBe(DEFAULT_THEME)
  })

  it('initTheme applies default theme to <html> when no saved preference', () => {
    const store = useThemeStore()
    store.initTheme()
    expect(document.documentElement.getAttribute('data-theme')).toBe(DEFAULT_THEME)
  })

  it('initTheme restores a persisted theme', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'linear')
    const store = useThemeStore()
    store.initTheme()
    expect(store.currentTheme).toBe('linear')
    expect(document.documentElement.getAttribute('data-theme')).toBe('linear')
  })

  it('setTheme updates state, DOM and persists', () => {
    const store = useThemeStore()
    store.setTheme('notion')
    expect(store.currentTheme).toBe('notion')
    expect(document.documentElement.getAttribute('data-theme')).toBe('notion')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('notion')
  })

  it('setTheme toggles dark class for dark themes and removes it for light', () => {
    const store = useThemeStore()
    store.setTheme('linear') // dark
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(store.isDark).toBe(true)
    store.setTheme('claude') // light
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(store.isDark).toBe(false)
  })

  it('setTheme ignores unknown theme keys', () => {
    const store = useThemeStore()
    store.setTheme('vercel')
    store.setTheme('not-a-real-theme')
    expect(store.currentTheme).toBe('vercel')
  })

  it('exposes all 9 themes', () => {
    const store = useThemeStore()
    expect(store.themes.length).toBe(9)
  })
})

describe('theme application consistency (property-based)', () => {
  beforeEach(() => {
    // reset DOM attributes so prior tests don't leak state into the property run
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.classList.remove('dark')
  })

  // Feature: ui-polish-refinement, Property 5: For any 主题 key t ∈ THEME_KEYS，调用 applyThemeToDom(t) 后，document.documentElement 的 data-theme 等于 t，且 dark class 的存在性与 getThemeMeta(t).dark 一致。
  // Validates: Requirements 15.1
  it('applyThemeToDom sets data-theme to t and dark class matches getThemeMeta(t).dark', () => {
    fc.assert(
      fc.property(fc.constantFrom(...THEME_KEYS), (t) => {
        // Each call fully determines DOM state (sets data-theme, toggles dark),
        // so the assertion does not depend on any prior iteration's state.
        applyThemeToDom(t)
        const html = document.documentElement
        expect(html.getAttribute('data-theme')).toBe(t)
        expect(html.classList.contains('dark')).toBe(!!getThemeMeta(t).dark)
      }),
      { numRuns: 100 }
    )
  })
})
