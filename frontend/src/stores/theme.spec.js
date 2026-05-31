import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

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

import { useThemeStore } from './theme'
import { DEFAULT_THEME, THEME_STORAGE_KEY } from '@/config/themes'

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
