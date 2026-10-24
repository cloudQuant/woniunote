import { describe, expect, it, vi } from 'vitest'
import { authEntryTarget, getAuthRedirect, safeInternalRedirect } from './authNavigation'

function makeRouter() {
  return {
    resolve(target) {
      const path = target.split(/[?#]/, 1)[0]
      return { path, matched: [{ path }] }
    }
  }
}

describe('auth navigation', () => {
  it('keeps parseable internal targets and excludes auth loops', () => {
    const router = makeRouter()

    expect(safeInternalRedirect('/write?draft=1#body', router)).toBe('/write?draft=1#body')
    expect(safeInternalRedirect('/login?redirect=%2Fwrite', router)).toBeNull()
    expect(safeInternalRedirect('/register', router)).toBeNull()
  })

  it.each([
    'https://outside.example/path',
    '//outside.example/path',
    '/\\\\outside.example/path',
    'javascript:alert(1)',
    ' /write',
    '/write/\u0001draft',
    '/write/\u007fdraft',
    ['/', '/write']
  ])('rejects unsafe redirect %s', (redirect) => {
    expect(safeInternalRedirect(redirect, makeRouter())).toBeNull()
  })

  it('rejects unresolved routes and router errors', () => {
    expect(safeInternalRedirect('/missing', { resolve: () => ({ matched: [] }) })).toBeNull()
    expect(safeInternalRedirect('/write', { resolve: () => null })).toBeNull()
    expect(safeInternalRedirect('/write', { resolve: () => { throw new Error('bad route') } })).toBeNull()
  })

  it('uses the local fallback origin and parsed path when route metadata is absent', () => {
    vi.stubGlobal('location', undefined)
    try {
      expect(safeInternalRedirect('/write/', { resolve: () => ({ matched: [{}] }) })).toBe('/write/')
      expect(safeInternalRedirect('/', { resolve: () => ({ matched: [{}], path: '' }) })).toBe('/')
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('carries only a validated target between login and registration', () => {
    const router = makeRouter()

    expect(authEntryTarget('Register', '/write', router)).toEqual({
      name: 'Register',
      query: { redirect: '/write' }
    })
    expect(authEntryTarget('Login', '//outside.example', router)).toEqual({ name: 'Login' })
  })

  it('extracts only a validated query redirect', () => {
    const router = makeRouter()
    expect(getAuthRedirect({ query: { redirect: '/write' } }, router)).toBe('/write')
    expect(getAuthRedirect({ query: { redirect: '/login' } }, router)).toBeNull()
    expect(getAuthRedirect({}, router)).toBeNull()
  })
})
