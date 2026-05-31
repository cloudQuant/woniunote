import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const routeState = vi.hoisted(() => ({ params: {} }))
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({ push })
}))

const m = vi.hoisted(() => ({
  msg: { success: vi.fn(), error: vi.fn() },
  articleApi: {
    create: vi.fn(() => Promise.resolve({ data: { articleid: 11 } })),
    update: vi.fn(() => Promise.resolve({ data: { articleid: 22 } })),
    getDetail: vi.fn(() => Promise.resolve({ data: {
      headline: 'X', type: 102, content: 'c', thumbnail: 't', credit: 0, drafted: 0
    } }))
  },
  uploadApi: { uploadImage: vi.fn(() => Promise.resolve({ data: { url: '/img.png' } })) }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/api', () => ({ articleApi: m.articleApi, uploadApi: m.uploadApi }))
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    fetchArticleTypes: vi.fn(() => Promise.resolve({})),
    articleTypes: { 1: '交易策略', 101: '股票策略', 102: '期货策略', 2: '量化框架' }
  })
}))
vi.mock('@/components/editor/UEditor.vue', () => ({
  default: { name: 'UEditor', render: () => null }
}))

import WriteArticle from './WriteArticle.vue'

describe('WriteArticle.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params = {}
  })

  it('builds categoryOptions with nested children', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    const opts = wrapper.vm.categoryOptions
    const trading = opts.find((o) => o.value === 1)
    expect(trading.children.map((c) => c.value)).toEqual([101, 102])
    // Category 2 has no children → children key removed.
    const framework = opts.find((o) => o.value === 2)
    expect(framework.children).toBeUndefined()
  })

  it('onTypeChange picks the last cascader value or null', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.onTypeChange([1, 102])
    expect(wrapper.vm.form.type).toBe(102)
    wrapper.vm.onTypeChange([])
    expect(wrapper.vm.form.type).toBe(null)
  })

  it('onEditorReady is callable', () => {
    const wrapper = mount(WriteArticle, mountOptions())
    expect(() => wrapper.vm.onEditorReady({})).not.toThrow()
  })

  it('uploadThumbnail sets thumbnail url', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    await wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })
    expect(wrapper.vm.form.thumbnail).toBe('/img.png')
    expect(m.msg.success).toHaveBeenCalledWith('上传成功')
  })

  it('publish creates a new article and navigates to detail', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'New'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.articleApi.create).toHaveBeenCalled()
    expect(m.msg.success).toHaveBeenCalledWith('发布成功')
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: 11 } })
  })

  it('saveDraft marks drafted and saves', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'Draft'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.saveDraft()
    expect(wrapper.vm.form.drafted).toBe(1)
    expect(m.msg.success).toHaveBeenCalledWith('草稿已保存')
  })

  it('saveArticle aborts on invalid form', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.publish()
    expect(m.articleApi.create).not.toHaveBeenCalled()
  })

  it('edit mode: loads article on mount and sets cascader path', async () => {
    routeState.params = { id: '22' }
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(wrapper.vm.isEdit).toBe(true)
    expect(m.articleApi.getDetail).toHaveBeenCalledWith('22')
    expect(wrapper.vm.form.headline).toBe('X')
    expect(wrapper.vm.form.typeArray).toEqual([1, 102])
  })

  it('edit mode: update navigates to returned article id', async () => {
    routeState.params = { id: '22' }
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Edited'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.articleApi.update).toHaveBeenCalledWith('22', expect.any(Object))
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: 22 } })
  })

  it('edit mode: fetch failure shows error and routes Home', async () => {
    routeState.params = { id: '99' }
    m.articleApi.getDetail.mockRejectedValueOnce(new Error('404'))
    mount(WriteArticle, mountOptions())
    await flushPromises()
    expect(m.msg.error).toHaveBeenCalledWith('文章不存在')
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
  })
})
