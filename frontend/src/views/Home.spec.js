import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, reactive } from 'vue'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

// Home.vue calls useRoute()/useRouter() at setup. Mock vue-router so mounting
// works without a real router; route.params.page drives currentPage.
const routeState = vi.hoisted(() => ({ current: null }))
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => routeState.current,
  useRouter: () => ({ push })
}))

// Stub the children with identifiable markers so the test stays focused on
// Home's own layout (ArticleList pulls in @/api, Sidebar pulls in stores/router).
vi.mock('@/components/article/ArticleList.vue', () => ({
  default: {
    name: 'ArticleList',
    props: ['page'],
    emits: ['page-change'],
    render() {
      return h('div', { class: 'stub-article-list' })
    }
  }
}))
vi.mock('@/components/sidebar/Sidebar.vue', () => ({
  default: {
    name: 'Sidebar',
    render() {
      return h('div', { class: 'stub-sidebar' })
    }
  }
}))

import Home from './Home.vue'

describe('Home.vue —— 布局结构（R2.1 / R2.3）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.current = reactive({ params: {}, query: {}, path: '/', name: 'Home' })
  })

  // R2.1: 首页样式中不得保留从不生效的死规则（.sidebar-wrapper 已在 Task 5.1 删除）。
  it('渲染结果不含任何 .sidebar-wrapper 元素', () => {
    const wrapper = mount(Home, mountOptions())
    expect(wrapper.find('.sidebar-wrapper').exists()).toBe(false)
  })

  // R2.3: 两栏布局（文章列表 + 侧边栏）在改动后仍维持正常结构。
  it('两栏结构存在：ArticleList 与 Sidebar 渲染于两个 el-col 中', () => {
    const wrapper = mount(Home, mountOptions())

    // 两个栅格列（:span="17" / :span="7"）。
    expect(wrapper.findAll('.el-col')).toHaveLength(2)

    // 文章列表与侧边栏均被渲染。
    const articleList = wrapper.findComponent({ name: 'ArticleList' })
    const sidebar = wrapper.findComponent({ name: 'Sidebar' })
    expect(articleList.exists()).toBe(true)
    expect(sidebar.exists()).toBe(true)

    // 文章列表位于主内容区内（左栏），侧边栏存在于布局中（右栏）。
    expect(wrapper.find('.main-content').exists()).toBe(true)
    expect(wrapper.find('.main-content .stub-article-list').exists()).toBe(true)
    expect(wrapper.find('.stub-sidebar').exists()).toBe(true)
  })

  // 文章列表接收由路由 page 参数驱动的 currentPage（默认 1）。
  it('currentPage 默认为 1 并作为 page 传入 ArticleList', () => {
    const wrapper = mount(Home, mountOptions())
    expect(wrapper.vm.currentPage).toBe(1)
    const articleList = wrapper.findComponent({ name: 'ArticleList' })
    expect(articleList.props('page')).toBe(1)
  })
})
