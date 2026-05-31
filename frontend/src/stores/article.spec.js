import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock the API module so the store can be tested without network.
vi.mock('@/api', () => ({
  articleApi: {
    getTypes: vi.fn(() => Promise.resolve({ data: { types: { 1: '交易策略', 701: 'python' } } })),
    getHot: vi.fn(() => Promise.resolve({
      data: { latest: [{ articleid: 1 }], most: [], recommended: [] }
    }))
  }
}))

import { useArticleStore } from './article'
import { articleApi } from '@/api'

describe('article store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchArticleTypes loads and caches types', async () => {
    const store = useArticleStore()
    const types = await store.fetchArticleTypes()
    expect(types[1]).toBe('交易策略')
    expect(articleApi.getTypes).toHaveBeenCalledTimes(1)

    // Second call should hit the cache, not the API again.
    await store.fetchArticleTypes()
    expect(articleApi.getTypes).toHaveBeenCalledTimes(1)
  })

  it('getTypeName returns name or fallback', async () => {
    const store = useArticleStore()
    await store.fetchArticleTypes()
    expect(store.getTypeName(701)).toBe('python')
    expect(store.getTypeName(99999)).toBe('未知分类')
  })

  it('fetchHotArticles populates hotArticles', async () => {
    const store = useArticleStore()
    const hot = await store.fetchHotArticles()
    expect(hot.latest.length).toBe(1)
    expect(store.hotArticles.latest[0].articleid).toBe(1)
  })
})
