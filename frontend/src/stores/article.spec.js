import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock the API module so the store can be tested without network.
vi.mock('@/api', () => ({
  articleApi: {
    getTypes: vi.fn(() => Promise.resolve({
      data: {
        types: { 1: '交易策略', 101: 'CTA策略', 701: 'python' },
        flat: [
          { id: 1, parent_id: null, name: '交易策略', sort_order: 10, visible: 1 },
          { id: 101, parent_id: 1, name: 'CTA策略', sort_order: 10, visible: 1 },
          { id: 701, parent_id: null, name: 'python', sort_order: 70, visible: 1 }
        ],
        tree: [
          { id: 1, parent_id: null, name: '交易策略', sort_order: 10, visible: 1, children: [
            { id: 101, parent_id: 1, name: 'CTA策略', sort_order: 10, visible: 1, children: [] }
          ] },
          { id: 701, parent_id: null, name: 'python', sort_order: 70, visible: 1, children: [] }
        ]
      }
    })),
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

  it('normalizes tree data for paths and cascader options', async () => {
    const store = useArticleStore()
    await store.fetchArticleTypes()
    expect(store.articleTypeFlat).toHaveLength(3)
    expect(store.articleTypeTree[0].children[0].id).toBe(101)
    expect(store.getTypePath(101)).toEqual([1, 101])
    expect(store.categoryOptions[0].children[0]).toEqual({ value: 101, label: 'CTA策略' })
  })

  it('refreshArticleTypes bypasses cache', async () => {
    const store = useArticleStore()
    await store.fetchArticleTypes()
    await store.refreshArticleTypes()
    expect(articleApi.getTypes).toHaveBeenCalledTimes(2)
  })

  it('fetchHotArticles populates hotArticles', async () => {
    const store = useArticleStore()
    const hot = await store.fetchHotArticles()
    expect(hot.latest.length).toBe(1)
    expect(store.hotArticles.latest[0].articleid).toBe(1)
  })
})
