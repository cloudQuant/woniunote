const AUTH_PATHS = new Set(['/login', '/register'])

function hasControlCharacters(value) {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    if (code < 0x20 || code === 0x7f) return true
  }
  return false
}

/**
 * Return a parsed, same-origin route target, excluding auth loops.
 * Query and hash are retained so protected deep links survive registration.
 */
export function safeInternalRedirect(value, router) {
  if (typeof value !== 'string' || !value || value.trim() !== value) return null
  if (!value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return null
  if (hasControlCharacters(value)) return null

  const origin = globalThis.location?.origin || 'http://localhost'
  let parsed
  let resolved
  try {
    parsed = new URL(value, origin)
    resolved = router?.resolve(value)
  } catch {
    return null
  }

  if (parsed.origin !== origin || !resolved) return null
  if (Array.isArray(resolved.matched) && resolved.matched.length === 0) return null

  const path = String(resolved.path || parsed.pathname).replace(/\/+$/, '').toLowerCase() || '/'
  if (AUTH_PATHS.has(path)) return null
  return value
}

export function authEntryTarget(name, redirect, router) {
  const target = safeInternalRedirect(redirect, router)
  return target ? { name, query: { redirect: target } } : { name }
}

export function getAuthRedirect(route, router) {
  return safeInternalRedirect(route?.query?.redirect, router)
}
