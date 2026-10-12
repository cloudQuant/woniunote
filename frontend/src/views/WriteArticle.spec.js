import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['log', 'error'])

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
  uploadApi: { uploadImage: vi.fn(() => Promise.resolve({ data: { url: '/img.png' } })) },
  store: {
    categoryOptions: [
      { value: 1, label: '交易策略', children: [
        { value: 101, label: '股票策略' },
        { value: 102, label: '期货策略' }
      ] },
      { value: 2, label: '量化框架' }
    ],
    getTypePath: vi.fn((type) => (type >= 100 ? [Math.floor(type / 100), type] : [type]))
  }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/api', () => ({ articleApi: m.articleApi, uploadApi: m.uploadApi }))
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    fetchArticleTypes: vi.fn(() => Promise.resolve({})),
    articleTypes: { 1: '交易策略', 101: '股票策略', 102: '期货策略', 2: '量化框架' },
    get categoryOptions() { return m.store.categoryOptions },
    getTypePath: m.store.getTypePath
  })
}))
vi.mock('@/components/editor/UEditor.vue', () => ({
  default: { name: 'UEditor', emits: ['update:modelValue', 'ready'], render: () => null }
}))

import WriteArticle from './WriteArticle.vue'

describe('WriteArticle.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params = {}
    m.store.categoryOptions = [
      { value: 1, label: '交易策略', children: [
        { value: 101, label: '股票策略' },
        { value: 102, label: '期货策略' }
      ] },
      { value: 2, label: '量化框架' }
    ]
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

  it('falls back to an empty category list when the store has none', () => {
    m.store.categoryOptions = null
    const wrapper = mount(WriteArticle, mountOptions())
    expect(wrapper.vm.categoryOptions).toEqual([])
  })

  it('two-way binds the editor fields to the form model', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.findComponent({ name: 'el-input' }).vm.$emit('update:modelValue', '标题')
    wrapper.findComponent({ name: 'UEditor' }).vm.$emit('update:modelValue', '<p>正文</p>')
    wrapper.findComponent({ name: 'el-cascader' }).vm.$emit('update:modelValue', [1, 101])
    wrapper.findComponent({ name: 'el-input-number' }).vm.$emit('update:modelValue', 30)
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.form.headline).toBe('标题')
    expect(wrapper.vm.form.content).toBe('<p>正文</p>')
    expect(wrapper.vm.form.typeArray).toEqual([1, 101])
    expect(wrapper.vm.form.credit).toBe(30)
  })

  it('UEditor ready callback is wired through the template', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    expect(() => wrapper.findComponent({ name: 'UEditor' }).vm.$emit('ready')).not.toThrow()
  })

  it('saveArticle aborts when the form ref is missing', async () => {
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.formRef = null
    await wrapper.vm.saveDraft()
    expect(m.articleApi.create).not.toHaveBeenCalled()
    expect(wrapper.vm.saving).toBe(false)
  })

  it('uploadThumbnail reports failures without throwing', async () => {
    m.uploadApi.uploadImage.mockRejectedValueOnce(new Error('upload down'))
    const wrapper = mount(WriteArticle, mountOptions())
    await expect(wrapper.vm.uploadThumbnail({ file: new Blob(['x']) })).resolves.toBeUndefined()
    expect(wrapper.vm.form.thumbnail).toBe('')
    expect(m.msg.success).not.toHaveBeenCalled()
  })

  it('saveArticle surfaces API failures and clears the loading flag', async () => {
    m.articleApi.create.mockRejectedValueOnce(new Error('save down'))
    const wrapper = mount(WriteArticle, mountOptions())
    wrapper.vm.form.headline = 'Boom'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(m.msg.success).not.toHaveBeenCalledWith('发布成功')
    expect(wrapper.vm.publishing).toBe(false)
    expect(push).not.toHaveBeenCalled()
  })

  it('edit mode falls back to the route id when update omits the article id', async () => {
    routeState.params = { id: '22' }
    m.articleApi.update.mockResolvedValueOnce({ data: null })
    const wrapper = mount(WriteArticle, mountOptions())
    await flushPromises()
    wrapper.vm.form.headline = 'Edited'
    wrapper.vm.form.type = 101
    wrapper.vm.form.content = 'body'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.publish()
    expect(push).toHaveBeenCalledWith({ name: 'ArticleDetail', params: { id: '22' } })
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
