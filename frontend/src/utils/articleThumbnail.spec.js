import { describe, expect, it } from 'vitest'
import {
  isValidArticleThumbnail,
  parseArticleThumbnail,
  resolveArticleThumbnailUrl
} from './articleThumbnail'

describe('article thumbnail contract', () => {
  it('accepts empty input, backend-safe basenames, legacy thumb routes, and upload paths', () => {
    expect(isValidArticleThumbnail('')).toBe(true)
    for (const basename of ['101.png', '_cover.png', '-cover.png', '.cover.png', 'a.b.c']) {
      expect(isValidArticleThumbnail(basename)).toBe(true)
      expect(parseArticleThumbnail(basename)).toMatchObject({ kind: 'basename', basename })
    }
    expect(parseArticleThumbnail('/api/thumb/101.png')).toMatchObject({
      kind: 'legacy-route', basename: '101.png'
    })
    expect(parseArticleThumbnail('/api/thumb/.cover.png')).toMatchObject({
      kind: 'legacy-route', basename: '.cover.png'
    })
    expect(parseArticleThumbnail('/uploads/uploads/images/2026/10/1_1000.png')).toMatchObject({
      kind: 'upload-path', basename: '1_1000.png'
    })
    expect(parseArticleThumbnail('/uploads/_archive/-2026/.images/cover.png')).toMatchObject({
      kind: 'upload-path', basename: 'cover.png'
    })
  })

  it('enforces the 512-byte ASCII limit', () => {
    const basename512 = `${'a'.repeat(510)}.x`
    const basename513 = `${'a'.repeat(511)}.x`
    const uploadPath512 = `/uploads/${'a'.repeat(501)}.x`
    const uploadPath513 = `/uploads/${'a'.repeat(502)}.x`

    expect(basename512).toHaveLength(512)
    expect(uploadPath512).toHaveLength(512)
    expect(isValidArticleThumbnail(basename512)).toBe(true)
    expect(isValidArticleThumbnail(uploadPath512)).toBe(true)
    expect(isValidArticleThumbnail(basename513)).toBe(false)
    expect(isValidArticleThumbnail(uploadPath513)).toBe(false)
    expect(isValidArticleThumbnail('é.png')).toBe(false)
  })

  it.each([
    'https://example.com/cover.png',
    'cover',
    'cover.',
    '.cover',
    'cover..png',
    'cover~.png',
    '/api/thumb/a/b.png',
    '/api/thumb/cover',
    '/api/thumb/cover.',
    '/uploads//cover.png',
    '/uploads/../cover.png',
    '/uploads/2026/./cover.png',
    '/uploads/2026/cover',
    '/uploads/2026/cover.',
    '/uploads/2026/.cover',
    '/uploads/2026//nested/cover.png',
    '/uploads/2026/a..png',
    '/uploads/a%2fb.png',
    '/uploads/a b.png',
    '/uploads/a\tb.png',
    '/uploads/a\\b.png',
    '/uploads/cover.png?size=2',
    '/uploads/cover.png#fragment',
    'cover..png'
  ])('rejects unsafe thumbnail value %s', (value) => {
    expect(isValidArticleThumbnail(value)).toBe(false)
    expect(parseArticleThumbnail(value)).toBeNull()
  })

  it('keeps upload paths unchanged and resolves legacy forms to the versioned thumb route', () => {
    const uploadedPath = '/uploads/uploads/images/2026/10/12_3456.png'
    expect(resolveArticleThumbnailUrl(uploadedPath, 101)).toBe(uploadedPath)
    expect(resolveArticleThumbnailUrl('12_3456.png', 101)).toBe('/api/thumb/12_3456.png?v3')
    expect(resolveArticleThumbnailUrl('/api/thumb/12_3456.png', 101))
      .toBe('/api/thumb/12_3456.png?v3')
  })

  it('uses the type image for empty or invalid historical values when requested', () => {
    expect(resolveArticleThumbnailUrl('', 101)).toBe('/api/thumb/101.png?v3')
    expect(resolveArticleThumbnailUrl('/unsafe/../cover.png', 101))
      .toBe('/api/thumb/101.png?v3')
    expect(resolveArticleThumbnailUrl('', 101, { fallbackForEmpty: false })).toBeNull()
    expect(resolveArticleThumbnailUrl('', null)).toBeNull()
  })
})
