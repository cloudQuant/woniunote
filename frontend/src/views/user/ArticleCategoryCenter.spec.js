import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const messages = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn()
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: (...args) => messages.success(...args),
    error: (...args) => messages.error(...args)
  }
}))

const api = vi.hoisted(() => ({
  adminApi: {
    getArticles: vi.fn(),
    updateArticleType: vi.fn()
  }
}))

vi.mock('@/api', () => api)

const articleStoreMock = vi.hoisted(() => ({
  refreshArticleTypes: vi.fn(),
  getTypeName: vi.fn((id) => `type-${id}`),
  categoryOptions: [
    { value: 1, label: '交易策略', children: [{ value: 101, label: 'CTA策略' }] },
    { value: 2, label: '量化框架' }
  ]
}))

vi.mock('@/stores/article', () => ({
  useArticleStore: () => articleStoreMock
}))

vi.mock('@/views/admin/ArticleCategoryManager.vue', () => ({
  default: {
    name: 'ArticleCategoryManager',
    emits: ['changed'],
    template: '<div class="category-manager-stub" @click="$emit(\'changed\')">分类维护</div>'
  }
}))

import ArticleCategoryCenter from './ArticleCategoryCenter.vue'

const articleRows = [
  { articleid: 1, headline: 'A', type: 1, drafted: 0, createtime: '2026-01-01' },
  { articleid: 2, headline: 'B', type: 2, drafted: 1, createtime: '2026-01-02' }
]

function mockArticleList(rows = articleRows) {
  api.adminApi.getArticles.mockResolvedValue({
    data: rows.map((row) => ({ ...row })),
    total: rows.length
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.adminApi.getArticles.mockReset()
  api.adminApi.updateArticleType.mockReset()
  articleStoreMock.refreshArticleTypes.mockReset()
  articleStoreMock.getTypeName.mockImplementation((id) => `type-${id}`)
  articleStoreMock.refreshArticleTypes.mockResolvedValue({})
  api.adminApi.updateArticleType.mockResolvedValue({})
  mockArticleList()
})

describe('ArticleCategoryCenter.vue', () => {
  it('loads article types and admin articles on mount', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(articleStoreMock.refreshArticleTypes).toHaveBeenCalled()
    expect(api.adminApi.getArticles).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    expect(wrapper.vm.articles).toHaveLength(2)
    expect(wrapper.vm.total).toBe(2)
  })

  it('filters articles by selected category', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    api.adminApi.getArticles.mockClear()
    wrapper.vm.typeFilter = 101
    await wrapper.vm.handleFilterChange()

    expect(wrapper.vm.currentPage).toBe(1)
    expect(api.adminApi.getArticles).toHaveBeenCalledWith({ page: 1, page_size: 10, type: 101 })
  })

  it('changes a single article category', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], 101)

    expect(api.adminApi.updateArticleType).toHaveBeenCalledWith(1, 101)
    expect(wrapper.vm.articles[0].type).toBe(101)
    expect(messages.success).toHaveBeenCalledWith('分类已更新')
  })

  it('reverts a single article category when update fails', async () => {
    api.adminApi.updateArticleType.mockRejectedValueOnce(new Error('update fail'))
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], 101)

    expect(wrapper.vm.articles[0].type).toBe(1)
    expect(wrapper.vm.isArticleChanging(1)).toBe(false)
    expect(messages.error).toHaveBeenCalledWith('update fail')
  })

  it('batch changes selected article categories', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    api.adminApi.getArticles.mockClear()
    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0], wrapper.vm.articles[1]])
    wrapper.vm.batchTargetType = 101
    await wrapper.vm.batchChangeType()

    expect(api.adminApi.updateArticleType).toHaveBeenCalledWith(1, 101)
    expect(api.adminApi.updateArticleType).toHaveBeenCalledWith(2, 101)
    expect(messages.success).toHaveBeenCalledWith('已更新 2 篇文章')
    expect(wrapper.vm.batchTargetType).toBeNull()
    expect(api.adminApi.getArticles).toHaveBeenCalledWith({ page: 1, page_size: 10 })
  })

  it('requires selection and target category before batch change', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.batchChangeType()
    expect(messages.error).toHaveBeenCalledWith('请选择文章')

    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0]])
    await wrapper.vm.batchChangeType()
    expect(messages.error).toHaveBeenCalledWith('请选择目标分类')
    expect(api.adminApi.updateArticleType).not.toHaveBeenCalled()
  })

  it('refreshes article options and list after category maintenance changes', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    articleStoreMock.refreshArticleTypes.mockClear()
    api.adminApi.getArticles.mockClear()
    await wrapper.vm.handleCategoriesChanged()

    expect(articleStoreMock.refreshArticleTypes).toHaveBeenCalled()
    expect(api.adminApi.getArticles).toHaveBeenCalledWith({ page: 1, page_size: 10 })
  })
})
