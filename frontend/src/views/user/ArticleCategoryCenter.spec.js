import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const messages = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn()
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: (...args) => messages.success(...args),
    error: (...args) => messages.error(...args),
    warning: (...args) => messages.warning(...args)
  }
}))

const api = vi.hoisted(() => ({
  articleApi: {
    getMyList: vi.fn(),
    updateType: vi.fn()
  },
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

// el-pagination 桩：声明 v-model 事件，避免 Vue 对未声明事件的告警（同 MathHistory.spec）。
const paginationStub = {
  name: 'el-pagination',
  props: ['currentPage', 'pageSize', 'total', 'layout'],
  emits: ['update:current-page', 'current-change'],
  template: '<div class="el-pagination" />'
}

const articleRows = [
  { articleid: 1, headline: 'A', type: 1, drafted: 0, createtime: '2026-01-01' },
  { articleid: 2, headline: 'B', type: 2, drafted: 1, createtime: '2026-01-02' }
]

function mockArticleList(rows = articleRows) {
  api.articleApi.getMyList.mockResolvedValue({
    data: rows.map((row) => ({ ...row })),
    total: 25
  })
  api.adminApi.getArticles.mockResolvedValue({
    data: rows.map((row) => ({ ...row })),
    total: 25
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.articleApi.getMyList.mockReset()
  api.articleApi.updateType.mockReset()
  api.adminApi.getArticles.mockReset()
  api.adminApi.updateArticleType.mockReset()
  articleStoreMock.refreshArticleTypes.mockReset()
  articleStoreMock.getTypeName.mockImplementation((id) => `type-${id}`)
  articleStoreMock.refreshArticleTypes.mockResolvedValue({})
  api.articleApi.updateType.mockResolvedValue({})
  api.adminApi.updateArticleType.mockResolvedValue({})
  mockArticleList()
})

describe('ArticleCategoryCenter.vue', () => {
  it('loads article types and paged personal articles on mount', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(articleStoreMock.refreshArticleTypes).toHaveBeenCalled()
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    expect(api.adminApi.getArticles).not.toHaveBeenCalled()
    expect(wrapper.vm.articles).toHaveLength(2)
    expect(wrapper.vm.total).toBe(25)
  })

  it('can open category maintenance as the initial tab', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions({ props: { initialTab: 'categories' } }))
    await flushPromises()

    expect(wrapper.vm.activeTab).toBe('categories')
    expect(wrapper.text()).toContain('分类维护')
  })

  it('filters articles by selected category', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    api.articleApi.getMyList.mockClear()
    wrapper.vm.typeFilter = 101
    await wrapper.vm.handleFilterChange()

    expect(wrapper.vm.currentPage).toBe(1)
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 1, page_size: 10, type: 101 })
  })

  it('changes a single article category', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], 101)

    expect(api.articleApi.updateType).toHaveBeenCalledWith(1, 101)
    expect(wrapper.vm.articles[0].type).toBe(101)
    expect(messages.success).toHaveBeenCalledWith('分类已更新')
  })

  it('reverts a single article category when update fails', async () => {
    api.articleApi.updateType.mockRejectedValueOnce(new Error('update fail'))
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

    api.articleApi.getMyList.mockClear()
    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0], wrapper.vm.articles[1]])
    wrapper.vm.batchTargetType = 101
    await wrapper.vm.batchChangeType()

    expect(api.articleApi.updateType).toHaveBeenCalledWith(1, 101)
    expect(api.articleApi.updateType).toHaveBeenCalledWith(2, 101)
    expect(messages.success).toHaveBeenCalledWith('已更新 2 篇文章')
    expect(wrapper.vm.batchTargetType).toBeNull()
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 1, page_size: 10 })
  })

  it('requires selection and target category before batch change', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.batchChangeType()
    expect(messages.error).toHaveBeenCalledWith('请选择文章')

    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0]])
    await wrapper.vm.batchChangeType()
    expect(messages.error).toHaveBeenCalledWith('请选择目标分类')
    expect(api.articleApi.updateType).not.toHaveBeenCalled()
  })

  it('refreshes article options and list after category maintenance changes', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    articleStoreMock.refreshArticleTypes.mockClear()
    api.articleApi.getMyList.mockClear()
    await wrapper.vm.handleCategoriesChanged()

    expect(articleStoreMock.refreshArticleTypes).toHaveBeenCalled()
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 1, page_size: 10 })
  })

  it('can opt into admin article APIs', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions({ props: { articleScope: 'admin' } }))
    await flushPromises()

    expect(api.adminApi.getArticles).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], 101)
    expect(api.adminApi.updateArticleType).toHaveBeenCalledWith(1, 101)
  })

  it('formats dates for the article table', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(wrapper.vm.formatDate('')).toBe('')
    expect(wrapper.vm.formatDate('2026-01-01')).not.toBe('')
  })

  it('binds tab, cascader and pagination v-models', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions({ stubs: { 'el-pagination': paginationStub } }))
    await flushPromises()

    wrapper.findComponent({ name: 'el-tabs' }).vm.$emit('update:modelValue', 'categories')
    await flushPromises()
    expect(wrapper.vm.activeTab).toBe('categories')

    const cascaders = wrapper.findAllComponents({ name: 'el-cascader' })
    cascaders[0].vm.$emit('update:modelValue', 101)
    cascaders[1].vm.$emit('update:modelValue', 202)
    await flushPromises()
    expect(wrapper.vm.typeFilter).toBe(101)
    expect(wrapper.vm.batchTargetType).toBe(202)

    api.articleApi.getMyList.mockClear()
    const pagination = wrapper.findComponent({ name: 'el-pagination' })
    pagination.vm.$emit('update:current-page', 2)
    pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(wrapper.vm.currentPage).toBe(2)
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 2, page_size: 10, type: 101 })
  })

  it('reports category and article loading failures', async () => {
    articleStoreMock.refreshArticleTypes.mockRejectedValueOnce(new Error('types boom'))
    api.articleApi.getMyList.mockRejectedValueOnce(new Error('list boom'))
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(messages.error).toHaveBeenCalledWith('types boom')
    expect(messages.error).toHaveBeenCalledWith('list boom')
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.vm.refreshingTypes).toBe(false)
  })

  it('uses fallback error messages when errors carry no message', async () => {
    articleStoreMock.refreshArticleTypes.mockRejectedValueOnce({})
    api.articleApi.getMyList.mockRejectedValueOnce({})
    mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(messages.error).toHaveBeenCalledWith('获取文章分类失败')
    expect(messages.error).toHaveBeenCalledWith('获取文章列表失败')
  })

  it('tolerates non-array article payloads and missing totals', async () => {
    api.articleApi.getMyList.mockResolvedValueOnce({ data: null })
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    expect(wrapper.vm.articles).toEqual([])
    expect(wrapper.vm.total).toBe(0)
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })

  it('ignores invalid or unchanged single-category updates', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()
    api.articleApi.updateType.mockClear()

    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], null)
    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], wrapper.vm.articles[0].type)

    expect(api.articleApi.updateType).not.toHaveBeenCalled()
    expect(wrapper.vm.isArticleChanging(1)).toBe(false)
  })

  it('uses a fallback message when a single update fails without a message', async () => {
    api.articleApi.updateType.mockRejectedValueOnce({})
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    await wrapper.vm.changeSingleArticleType(wrapper.vm.articles[0], 101)

    expect(messages.error).toHaveBeenCalledWith('分类更新失败')
    expect(wrapper.vm.articles[0].type).toBe(1)
  })

  it('batch changes categories in admin scope', async () => {
    const wrapper = mount(ArticleCategoryCenter, mountOptions({ props: { articleScope: 'admin' } }))
    await flushPromises()

    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0]])
    wrapper.vm.batchTargetType = 101
    await wrapper.vm.batchChangeType()

    expect(api.adminApi.updateArticleType).toHaveBeenCalledWith(1, 101)
    expect(api.articleApi.updateType).not.toHaveBeenCalled()
    expect(messages.success).toHaveBeenCalledWith('已更新 1 篇文章')
  })

  it('reports batch failures with a fallback message', async () => {
    api.articleApi.updateType.mockRejectedValueOnce({})
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0]])
    wrapper.vm.batchTargetType = 101
    await wrapper.vm.batchChangeType()

    expect(messages.error).toHaveBeenCalledWith('批量修改失败')
    expect(wrapper.vm.batchChanging).toBe(false)
  })

  it('refreshes the list and reports partial success when only some updates fail', async () => {
    api.articleApi.updateType
      .mockResolvedValueOnce({ data: {} })
      .mockRejectedValueOnce(new Error('boom'))
    const wrapper = mount(ArticleCategoryCenter, mountOptions())
    await flushPromises()

    api.articleApi.getMyList.mockClear()
    wrapper.vm.handleSelectionChange([wrapper.vm.articles[0], wrapper.vm.articles[1]])
    wrapper.vm.batchTargetType = 101
    await wrapper.vm.batchChangeType()

    // 部分成功：给出准确计数而非误报全部失败
    expect(messages.warning).toHaveBeenCalledWith('已更新 1 篇，1 篇失败')
    // 部分失败也必须刷新列表，保持前端展示与后端状态一致
    expect(api.articleApi.getMyList).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    expect(wrapper.vm.batchChanging).toBe(false)
  })
})
