import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

// Sidebar uses useRouter() at setup; provide a stub so mounting works.
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

// Mock the article store so importing Sidebar.vue does not pull in @/api
// (axios/router/element-plus). Provide hotArticles + the async fetchers the
// component calls in onMounted.
const m = vi.hoisted(() => ({
  fetchHotArticles: vi.fn(() => Promise.resolve({})),
  fetchArticleTypes: vi.fn(() => Promise.resolve({}))
}))
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    hotArticles: { most: [], recommended: [] },
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
