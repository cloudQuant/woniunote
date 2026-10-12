import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

// Sidebar uses useRouter() at setup; provide a stub so mounting works.
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

// Mock the article store so importing Sidebar.vue does not pull in @/api
// (axios/router/element-plus). Provide hotArticles + the async fetchers the
// component calls in onMounted. `hot` is mutable so tests can drive the
// rendered lists.
const m = vi.hoisted(() => ({
  fetchHotArticles: vi.fn(() => Promise.resolve({})),
  fetchArticleTypes: vi.fn(() => Promise.resolve({})),
  hot: { most: [], recommended: [] }
}))
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    get hotArticles() { return m.hot },
    fetchHotArticles: m.fetchHotArticles,
    fetchArticleTypes: m.fetchArticleTypes
  })
}))

import Sidebar from './Sidebar.vue'

describe('Sidebar.vue —— 回到顶部键盘可达性 (R11.1/R11.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // scrollToTop calls window.scrollTo({ top: 0, behavior: 'smooth' }).
    window.scrollTo = vi.fn()
    m.hot = { most: [], recommended: [] }
  })

  it('.back-to-top 具备 role="button" 与 tabindex="0"', () => {
    const wrapper = mount(Sidebar, mountOptions())
    const btn = wrapper.find('.back-to-top')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('role')).toBe('button')
    expect(btn.attributes('tabindex')).toBe('0')
  })

  it('click 触发 scrollToTop（滚动到顶部）', async () => {
    const wrapper = mount(Sidebar, mountOptions())
    wrapper.vm.showBackToTop = true
    await nextTick()
    await wrapper.find('.back-to-top').trigger('click')
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('keydown.enter 触发与 click 相同的 scrollToTop', async () => {
    const wrapper = mount(Sidebar, mountOptions())
    wrapper.vm.showBackToTop = true
    await nextTick()
    await wrapper.find('.back-to-top').trigger('keydown.enter')
    expect(window.scrollTo).toHaveBeenCalledTimes(1)
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('keydown.space 触发与 click 相同的 scrollToTop', async () => {
    const wrapper = mount(Sidebar, mountOptions())
    wrapper.vm.showBackToTop = true
    await nextTick()
    await wrapper.find('.back-to-top').trigger('keydown.space')
    expect(window.scrollTo).toHaveBeenCalledTimes(1)
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })
})

describe('Sidebar.vue —— 搜索与滚动联动', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.scrollTo = vi.fn()
    m.hot = { most: [], recommended: [] }
    // jsdom keeps scrollY read-only; make it settable for the scroll tests.
    Object.defineProperty(window, 'scrollY', { configurable: true, writable: true, value: 0 })
  })

  it('handleSearch 仅对非空关键字跳转搜索结果页', () => {
    const wrapper = mount(Sidebar, mountOptions())
    wrapper.vm.searchKeyword = '   '
    wrapper.vm.handleSearch()
    expect(push).not.toHaveBeenCalled()
    wrapper.vm.searchKeyword = 'vue'
    wrapper.vm.handleSearch()
    expect(push).toHaveBeenCalledWith({ name: 'Search', query: { keyword: 'vue' } })
  })

  it('搜索框 v-model 与回车键都接线到 handleSearch', async () => {
    const wrapper = mount(Sidebar, mountOptions())
    const input = wrapper.findComponent({ name: 'el-input' })
    input.vm.$emit('update:modelValue', '量化')
    await nextTick()
    expect(wrapper.vm.searchKeyword).toBe('量化')
    await wrapper.find('.el-input').trigger('keyup.enter')
    expect(push).toHaveBeenCalledWith({ name: 'Search', query: { keyword: '量化' } })
  })

  it('handleScroll 按 300px 阈值切换回到顶部按钮', async () => {
    const wrapper = mount(Sidebar, mountOptions())
    await flushPromises() // onMounted awaits the fetchers before binding scroll
    window.scrollY = 120
    window.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(wrapper.vm.showBackToTop).toBe(false)
    window.scrollY = 400
    window.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(wrapper.vm.showBackToTop).toBe(true)
  })

  it('卸载时移除滚动监听', async () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const wrapper = mount(Sidebar, mountOptions())
    await flushPromises()
    wrapper.unmount()
    expect(removeSpy).toHaveBeenCalledWith('scroll', expect.any(Function))
    removeSpy.mockRestore()
  })

  it('渲染热门文章与推荐文章列表，空数据时显示占位', async () => {
    m.hot = {
      most: [{ articleid: 1, headline: '热文一' }],
      recommended: [{ articleid: 2, headline: '推荐一' }]
    }
    const wrapper = mount(Sidebar, mountOptions())
    await nextTick()
    expect(wrapper.findAll('.article-list a')).toHaveLength(2)
    expect(wrapper.text()).toContain('热文一')
    expect(wrapper.text()).toContain('推荐一')
    expect(wrapper.find('.empty-tip').exists()).toBe(false)

    m.hot = { most: [], recommended: [] }
    const empty = mount(Sidebar, mountOptions())
    await nextTick()
    expect(empty.find('.empty-tip').exists()).toBe(true)
  })

  it('挂载时加载热门文章与分类数据', async () => {
    mount(Sidebar, mountOptions())
    await flushPromises()
    expect(m.fetchHotArticles).toHaveBeenCalled()
    expect(m.fetchArticleTypes).toHaveBeenCalled()
  })
})
