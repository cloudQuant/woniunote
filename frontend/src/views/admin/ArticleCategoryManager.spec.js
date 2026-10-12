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

  it('renders current category overview with paths and article counts', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('当前分类3')
    expect(text).toContain('顶级分类2')
    expect(text).toContain('已关联文章2')
    expect(text).toContain('交易策略 / CTA策略')
    expect(text).toContain('2 篇')
  })

  it('builds display rows from flat categories when tree is empty', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        flat: [
          { id: 1, parent_id: null, name: '交易策略', sort_order: 10, visible: 1, article_count: 0 },
          { id: 101, parent_id: 1, name: 'CTA策略', sort_order: 10, visible: 1, article_count: 1 }
        ],
        tree: []
      }
    })

    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    expect(wrapper.vm.flatRows.map((row) => [row.id, row.depth])).toEqual([[1, 0], [101, 1]])
    expect(wrapper.text()).toContain('交易策略 / CTA策略')
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

  it('refresh button reloads the category list', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    m.adminApi.getArticleCategories.mockClear()
    const refresh = wrapper.findAllComponents({ name: 'el-button' })
      .find((b) => b.text().includes('刷新'))
    expect(refresh).toBeTruthy()
    refresh.vm.$emit('click')
    await flushPromises()
    expect(m.adminApi.getArticleCategories).toHaveBeenCalledTimes(1)
  })

  it('dialog and editor form controls are two-way bound', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    const dialogs = wrapper.findAllComponents({ name: 'el-dialog' })
    expect(dialogs).toHaveLength(2)
    dialogs[0].vm.$emit('update:modelValue', true)
    dialogs[1].vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(wrapper.vm.editorVisible).toBe(true)
    expect(wrapper.vm.deleteVisible).toBe(true)

    wrapper.findComponent({ name: 'el-input' }).vm.$emit('update:modelValue', '新名字')
    wrapper.findComponent({ name: 'el-input-number' }).vm.$emit('update:modelValue', 5)
    wrapper.findComponent({ name: 'el-switch' }).vm.$emit('update:modelValue', false)
    const selects = wrapper.findAllComponents({ name: 'el-select' })
    expect(selects).toHaveLength(2)
    selects[0].vm.$emit('update:modelValue', 2) // parent node
    selects[1].vm.$emit('update:modelValue', 3) // migration target
    await flushPromises()

    expect(wrapper.vm.editForm.name).toBe('新名字')
    expect(wrapper.vm.editForm.sort_order).toBe(5)
    expect(wrapper.vm.editForm.visible).toBe(false)
    expect(wrapper.vm.editForm.parent_id).toBe(2)
    expect(wrapper.vm.moveArticlesTo).toBe(3)
  })

  it('loadCategories surfaces API failures', async () => {
    m.adminApi.getArticleCategories.mockRejectedValueOnce(new Error('boom'))
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(m.msg.error).toHaveBeenCalledWith('boom')
    expect(wrapper.vm.loading).toBe(false)
  })

  it('loadCategories falls back to a generic message when the error has none', async () => {
    m.adminApi.getArticleCategories.mockRejectedValueOnce({})
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(m.msg.error).toHaveBeenCalledWith('获取分类失败')
    expect(wrapper.vm.flatRows).toEqual([])
  })

  it('saveCategory rejects a blank name', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openCreate()
    wrapper.vm.editForm.name = '   '
    await wrapper.vm.saveCategory()
    expect(m.msg.error).toHaveBeenCalledWith('分类名称不能为空')
    expect(m.adminApi.createArticleCategory).not.toHaveBeenCalled()
  })

  it('saveCategory reports API failures and clears the saving flag', async () => {
    m.adminApi.createArticleCategory.mockRejectedValueOnce(new Error('save fail'))
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openCreate()
    wrapper.vm.editForm.name = 'X'
    await wrapper.vm.saveCategory()
    expect(m.msg.error).toHaveBeenCalledWith('save fail')
    expect(wrapper.vm.saving).toBe(false)
    expect(wrapper.vm.editorVisible).toBe(true)
  })

  it('openCreate() with no parent builds a root payload', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openCreate()
    expect(wrapper.vm.editForm.parent_id).toBe(0)
    expect(wrapper.vm.editForm.visible).toBe(true)
    wrapper.vm.editForm.name = '顶级'
    await wrapper.vm.saveCategory()
    expect(m.adminApi.createArticleCategory).toHaveBeenCalledWith({
      name: '顶级',
      parent_id: null,
      sort_order: 0,
      visible: 1
    })
  })

  it('openEdit tolerates rows without parent or sort order', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openEdit({ id: 9, name: '裸节点', visible: 1 })
    expect(wrapper.vm.editForm.parent_id).toBe(0)
    expect(wrapper.vm.editForm.sort_order).toBe(0)
    expect(wrapper.vm.editingId).toBe(9)
  })

  it('parentOptions excludes the edited node and its descendants', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.openEdit(wrapper.vm.flatRows[0]) // id 1 with descendant 101
    expect(wrapper.vm.parentOptions.map((o) => o.id)).toEqual([0, 2])
  })

  it('toggleVisible flips the flag in both directions', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    await wrapper.vm.toggleVisible(wrapper.vm.flatRows[0]) // visible → hide
    expect(m.adminApi.updateArticleCategory).toHaveBeenCalledWith(1, { visible: 0 })
    expect(m.msg.success).toHaveBeenCalledWith('分类已隐藏')

    m.adminApi.updateArticleCategory.mockClear()
    m.msg.success.mockClear()
    await wrapper.vm.toggleVisible({ id: 2, name: '编程', visible: 0 }) // hidden → show
    expect(m.adminApi.updateArticleCategory).toHaveBeenCalledWith(2, { visible: 1 })
    expect(m.msg.success).toHaveBeenCalledWith('分类已显示')
  })

  it('toggleVisible reports failures', async () => {
    m.adminApi.updateArticleCategory.mockRejectedValueOnce(new Error('nope'))
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    await wrapper.vm.toggleVisible(wrapper.vm.flatRows[0])
    expect(m.msg.error).toHaveBeenCalledWith('nope')
  })

  it('requestDelete deletes an empty category after confirmation', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    await wrapper.vm.requestDelete(wrapper.vm.flatRows[1]) // article_count 0
    expect(m.box.confirm).toHaveBeenCalled()
    expect(wrapper.vm.deleteVisible).toBe(false)
    expect(m.adminApi.deleteArticleCategory).toHaveBeenCalledWith(101, {})
    expect(m.msg.success).toHaveBeenCalledWith('分类已删除')
  })

  it('requestDelete ignores cancellations but reports real failures', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    m.box.confirm.mockRejectedValueOnce('cancel')
    await wrapper.vm.requestDelete(wrapper.vm.flatRows[1])
    expect(m.msg.error).not.toHaveBeenCalled()

    m.box.confirm.mockRejectedValueOnce(new Error('confirm blew up'))
    await wrapper.vm.requestDelete(wrapper.vm.flatRows[1])
    expect(m.msg.error).toHaveBeenCalledWith('confirm blew up')
  })

  it('confirmDeleteWithMove requires a migration target', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    wrapper.vm.deleteTarget = wrapper.vm.flatRows[0]
    wrapper.vm.moveArticlesTo = null
    await wrapper.vm.confirmDeleteWithMove()
    expect(m.msg.error).toHaveBeenCalledWith('请选择迁移目标分类')
    expect(m.adminApi.deleteArticleCategory).not.toHaveBeenCalled()
  })

  it('performDelete surfaces API errors and clears the deleting flag', async () => {
    m.adminApi.deleteArticleCategory.mockRejectedValueOnce(new Error('del fail'))
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    await wrapper.vm.performDelete(1, {})
    expect(m.msg.error).toHaveBeenCalledWith('del fail')
    expect(wrapper.vm.deleting).toBe(false)
  })

  it('builds paths from the flat list when the tree payload is missing', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        flat: [{ id: 1, parent_id: null, name: '交易策略', sort_order: 1, visible: 1, article_count: 0 }],
        tree: null
      }
    })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(wrapper.vm.flatRows.map((r) => r.id)).toEqual([1])
    expect(wrapper.vm.categoryPathRows[0].path).toBe('交易策略')
  })

  it('falls back to the row name when no flat lookup is available', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        tree: [{ id: 1, name: '交易策略', parent_id: null, sort_order: 1, visible: 1, article_count: 0, children: [] }]
      }
    })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(wrapper.vm.categoryPathRows[0].path).toBe('交易策略')
  })

  it('tolerates an empty/absent payload and tree nodes without children', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({ data: null })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(wrapper.vm.flatRows).toEqual([])

    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: { tree: [{ id: 7, name: '裸节点', parent_id: null, sort_order: 1, visible: 1 }] }
    })
    const second = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(second.vm.flatRows.map((r) => [r.id, r.depth])).toEqual([[7, 0]])

    // Defensive guards: null inputs must not throw.
    second.vm.categoriesTree = null
    await second.vm.$nextTick()
    expect(second.vm.flatRows).toEqual([])
    expect(second.vm.buildTreeFromFlat(null)).toEqual([])
    expect(second.vm.buildTreeFromFlat(undefined)).toEqual([])
  })

  it('isDescendant walks multi-level parent chains', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        flat: [
          { id: 1, parent_id: null, name: 'A', sort_order: 1, visible: 1, article_count: 0 },
          { id: 101, parent_id: 1, name: 'B', sort_order: 1, visible: 1, article_count: 0 },
          { id: 10101, parent_id: 101, name: 'C', sort_order: 1, visible: 1, article_count: 0 }
        ],
        tree: []
      }
    })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(wrapper.vm.isDescendant(10101, 1)).toBe(true) // two hops up
    expect(wrapper.vm.isDescendant(101, 1)).toBe(true) // one hop up
    expect(wrapper.vm.isDescendant(101, 999)).toBe(false)
    expect(wrapper.vm.isDescendant(1, 1)).toBe(false) // root has no parent
    // Deeper rows still resolve their breadcrumb path.
    expect(wrapper.vm.categoryPathRows.map((r) => r.path))
      .toEqual(['A', 'A / B', 'A / B / C'])
  })

  it('new top-level button opens the create dialog', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    const create = wrapper.findAllComponents({ name: 'el-button' })
      .find((b) => b.text().includes('新增顶级分类'))
    expect(create).toBeTruthy()
    create.vm.$emit('click')
    await flushPromises()
    expect(wrapper.vm.editorVisible).toBe(true)
    expect(wrapper.vm.editingId).toBe(null)
  })

  it('breaks sort ties by id and defaults a missing sort_order to 0', async () => {
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        flat: [
          { id: 5, name: 'B', parent_id: null, sort_order: 10, visible: 1, article_count: 0 },
          { id: 2, name: 'A', parent_id: null, sort_order: 10, visible: 1, article_count: 0 },
          { id: 9, name: 'C', parent_id: null, visible: 1, article_count: 0 }
        ],
        tree: []
      }
    })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    expect(wrapper.vm.flatRows.map((r) => r.id)).toEqual([9, 2, 5])
  })

  it('uses generic fallbacks when mutation errors carry no message', async () => {
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()

    m.adminApi.createArticleCategory.mockRejectedValueOnce({})
    wrapper.vm.openCreate()
    wrapper.vm.editForm.name = 'X'
    await wrapper.vm.saveCategory()
    expect(m.msg.error).toHaveBeenCalledWith('保存失败')

    m.adminApi.updateArticleCategory.mockRejectedValueOnce({})
    await wrapper.vm.toggleVisible(wrapper.vm.flatRows[0])
    expect(m.msg.error).toHaveBeenCalledWith('操作失败')

    m.box.confirm.mockRejectedValueOnce({})
    await wrapper.vm.requestDelete(wrapper.vm.flatRows[1])
    expect(m.msg.error).toHaveBeenCalledWith('删除失败')

    m.adminApi.deleteArticleCategory.mockRejectedValueOnce({})
    await wrapper.vm.performDelete(1, {})
    expect(m.msg.error).toHaveBeenCalledWith('删除失败')
  })

  it('sorts siblings by sort_order then id and emits changed after mutations', async () => {
    // Only the flat-fallback path sorts; an explicit tree is trusted as-is.
    m.adminApi.getArticleCategories.mockResolvedValueOnce({
      data: {
        flat: [
          { id: 3, name: '后', parent_id: null, sort_order: 20, visible: 1, article_count: 0 },
          { id: 2, name: '先', parent_id: null, sort_order: 10, visible: 1, article_count: 0 },
          { id: 1, name: '默认排序', parent_id: null, sort_order: 0, visible: 1, article_count: 0 }
        ],
        tree: []
      }
    })
    const wrapper = mount(ArticleCategoryManager, mountOptions())
    await flushPromises()
    // sort_order 0 must fall back to 0 (not NaN) in the comparator.
    expect(wrapper.vm.flatRows.map((r) => r.id)).toEqual([1, 2, 3])

    await wrapper.vm.toggleVisible(wrapper.vm.flatRows[0])
    expect(wrapper.emitted('changed')).toBeTruthy()
  })
})
