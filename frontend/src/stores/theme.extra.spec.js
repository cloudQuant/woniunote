import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

/**
 * Covers theme store branches not exercised by theme.spec.js:
 *   - first-visit prefers-color-scheme: dark → 'linear'
 *   - localStorage throwing (private mode) is swallowed
 *   - applyThemeToDom with unknown key is a no-op
 */

describe('theme store — system preference & resilience', () => {
  let originalMatchMedia
  beforeEach(() => {
    setActivePinia(createPinia())
    originalMatchMedia = window.matchMedia
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.classList.remove('dark')
  })
  afterEach(() => {
    window.matchMedia = originalMatchMedia
    vi.restoreAllMocks()
  })

  it('initTheme picks dark default when system prefers dark and no saved theme', async () => {
    // No saved preference.
    const lsStub = {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {}
    }
    vi.stubGlobal('localStorage', lsStub)
    window.matchMedia = vi.fn(() => ({ matches: true }))

    const { useThemeStore } = await import('./theme')
    const store = useThemeStore()
    store.initTheme()
    expect(store.currentTheme).toBe('linear')
    expect(store.isDark).toBe(true)
  })

  it('initTheme falls back to default when localStorage throws', async () => {
    const throwingLs = {
      getItem: () => { throw new Error('blocked') },
      setItem: () => { throw new Error('blocked') },
      removeItem: () => {}
    }
    vi.stubGlobal('localStorage', throwingLs)
    window.matchMedia = vi.fn(() => ({ matches: false }))

    const { useThemeStore } = await import('./theme')
    const store = useThemeStore()
    store.initTheme()
    expect(store.currentTheme).toBe('claude')
  })

  it('setTheme swallows localStorage write errors', async () => {
    const throwingLs = {
      getItem: () => null,
      setItem: () => { throw new Error('quota') },
      removeItem: () => {}
    }
    vi.stubGlobal('localStorage', throwingLs)
    const { useThemeStore } = await import('./theme')
    const store = useThemeStore()
    expect(() => store.setTheme('notion')).not.toThrow()
    expect(store.currentTheme).toBe('notion')
  })

  it('applyThemeToDom ignores unknown keys', async () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null, setItem: () => {}, removeItem: () => {}
    })
    const { applyThemeToDom } = await import('./theme')
    document.documentElement.removeAttribute('data-theme')
    applyThemeToDom('does-not-exist')
    expect(document.documentElement.getAttribute('data-theme')).toBe(null)
  })
})
