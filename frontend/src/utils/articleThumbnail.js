export const ARTICLE_THUMBNAIL_CACHE_VERSION = 'v3'
export const MAX_ARTICLE_THUMBNAIL_LENGTH = 512

function isSafeThumbnailString(value) {
  return typeof value === 'string' &&
    value.length <= MAX_ARTICLE_THUMBNAIL_LENGTH &&
    /^[A-Za-z0-9_./-]+$/.test(value) &&
    !value.includes('..')
}

function isSafeBasename(filename) {
  if (!filename || filename.includes('/')) return false
  const extensionSeparator = filename.lastIndexOf('.')
  return extensionSeparator > 0 && extensionSeparator < filename.length - 1
}

function isSafeUploadsPath(path) {
  if (!path.startsWith('/uploads/')) return false

  const segments = path.slice('/uploads/'.length).split('/')
  const directories = segments.slice(0, -1)
  if (directories.some((segment) => !segment || segment === '.' || segment === '..')) {
    return false
  }
  return isSafeBasename(segments[segments.length - 1])
}

/**
 * Parse the thumbnail representations accepted by the article API.
 * Upload paths remain canonical; legacy basenames and thumb routes are
 * normalized to a basename only for display.
 */
export function parseArticleThumbnail(value) {
  if (!isSafeThumbnailString(value)) return null

  if (value.startsWith('/uploads/')) {
    if (!isSafeUploadsPath(value)) return null
    const segments = value.slice('/uploads/'.length).split('/')
    return {
      kind: 'upload-path',
      value,
      basename: segments[segments.length - 1]
    }
  }

  if (value.startsWith('/api/thumb/')) {
    const basename = value.slice('/api/thumb/'.length)
    if (!isSafeBasename(basename)) return null
    return { kind: 'legacy-route', value, basename }
  }

  if (isSafeBasename(value)) {
    return { kind: 'basename', value, basename: value }
  }

  return null
}

export function isValidArticleThumbnail(value) {
  return value === '' || parseArticleThumbnail(value) !== null
}

function typeThumbnailBasename(type) {
  if (!type) return null
  const basename = `${type}.png`
  return parseArticleThumbnail(basename)?.kind === 'basename' ? basename : null
}

/**
 * Resolve a canonical thumbnail to the URL used in an img element.
 * `fallbackForEmpty: false` keeps the editor's empty uploader state visible;
 * invalid historical values still fall back to the article type image.
 */
export function resolveArticleThumbnailUrl(
  value,
  type,
  { fallbackForEmpty = true } = {}
) {
  const parsed = parseArticleThumbnail(value)
  if (parsed?.kind === 'upload-path') return parsed.value
  if (parsed) return `/api/thumb/${parsed.basename}?${ARTICLE_THUMBNAIL_CACHE_VERSION}`

  if ((value === '' || value === null || value === undefined) && !fallbackForEmpty) {
    return null
  }

  const fallbackBasename = typeThumbnailBasename(type)
  return fallbackBasename
    ? `/api/thumb/${fallbackBasename}?${ARTICLE_THUMBNAIL_CACHE_VERSION}`
    : null
}
