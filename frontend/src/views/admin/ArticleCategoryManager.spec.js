import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const m = vi.hoisted(() => ({
  msg: { success: vi.fn(), error: vi.fn() },
  box: { confirm: vi.fn(() => Promise.resolve()) },
  adminApi: {
    getArticleCategories: vi.fn(() => Promise.resolve({
      data: {
        flat: [
          { id: 1, parent_id: null, name: '交易策略', sort_order: 10, visible: 1, article_count: 2 },
          { id: 101, parent_id: 1, name: 'CTA策略', sort_order: 10, visible: 1, article_count: 0 },
          { id: 2, parent_id: null, name: '编程', sort_order: 20, visible: 1, article_count: 0 }
        ],
        tree: [
          { id: 1, parent_id: null, name: '交易策略', sort_order: 10, visible: 1, article_count: 2, children: [
            { id: 101, parent_id: 1, name: 'CTA策略', sort_order: 10, visible: 1, article_count: 0, children: [] }
          ] },
          { id: 2, parent_id: null, name: '编程', sort_order: 20, visible: 1, article_count: 0, children: [] }
        ]
      }
    })),
    createArticleCategory: vi.fn(() => Promise.resolve({})),
    updateArticleCategory: vi.fn(() => Promise.resolve({})),
    deleteArticleCategory: vi.fn(() => Promise.resolve({}))
  }
}))

vi.mock('element-plus', () => ({ ElMessage: m.msg, ElMessageBox: m.box }))
vi.mock('@/api', () => ({ adminApi: m.adminApi }))

import ArticleCategoryManager from './ArticleCategoryManager.vue'

describe('ArticleCategoryManager.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads categories and flattens tree rows with depth', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(m.adminApi.getArticleCategories).toHaveBeenCalled()
    expect(wrapper.vm.flatRows.map((row) => [row.id, row.depth])).toEqual([[1, 0], [101, 1], [2, 0]])
  })

  it('creates a child category with selected parent', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openCreate(wrapper.vm.flatRows[0])
    wrapper.vm.editForm.name = '新子分类'
    await wrapper.vm.saveCategory()
    expect(m.adminApi.createArticleCategory).toHaveBeenCalledWith({
      name: '新子分类',
      parent_id: 1,
      sort_order: 0,
      visible: 1
    })
    expect(m.msg.success).toHaveBeenCalledWith('分类已创建')
  })

  it('updates an existing category', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openEdit(wrapper.vm.flatRows[1])
    wrapper.vm.editForm.name = 'CTA改名'
    wrapper.vm.editForm.visible = false
    await wrapper.vm.saveCategory()
    expect(m.adminApi.updateArticleCategory).toHaveBeenCalledWith(101, {
      name: 'CTA改名',
      parent_id: 1,
      sort_order: 10,
      visible: 0
    })
  })

  it('requires move target when deleting a category with articles', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    await wrapper.vm.requestDelete(wrapper.vm.flatRows[0])
    expect(wrapper.vm.deleteVisible).toBe(true)
    wrapper.vm.moveArticlesTo = 2
    await wrapper.vm.confirmDeleteWithMove()
    expect(m.adminApi.deleteArticleCategory).toHaveBeenCalledWith(1, { move_articles_to: 2 })
  })
})
