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
  it('两栏结构存在，并标记可在桌面端将侧边栏排到左侧的列', () => {
    const wrapper = mount(Home, mountOptions())

    // 两个栅格列（:span="17" / :span="7"）。
    expect(wrapper.findAll('.el-col')).toHaveLength(2)

    // 文章列表与侧边栏均被渲染。
    const articleList = wrapper.findComponent({ name: 'ArticleList' })
    const sidebar = wrapper.findComponent({ name: 'Sidebar' })
    expect(articleList.exists()).toBe(true)
    expect(sidebar.exists()).toBe(true)

    // 文章列表与侧边栏分别具有布局类；实际左右位置由 Home.vue 的 scoped CSS 控制。
    expect(wrapper.find('.main-content').exists()).toBe(true)
    expect(wrapper.find('.main-content .stub-article-list').exists()).toBe(true)
    expect(wrapper.find('.stub-sidebar').exists()).toBe(true)
    expect(wrapper.find('.home-main-column').exists()).toBe(true)
    expect(wrapper.find('.home-sidebar-column').exists()).toBe(true)
  })

  // 文章列表接收由路由 page 参数驱动的 currentPage（默认 1）。
  it('currentPage 默认为 1 并作为 page 传入 ArticleList', () => {
    const wrapper = mount(Home, mountOptions())
    expect(wrapper.vm.currentPage).toBe(1)
    const articleList = wrapper.findComponent({ name: 'ArticleList' })
    expect(articleList.props('page')).toBe(1)
  })

  it('currentPage 解析 /page/:page 路由参数', () => {
    routeState.current = reactive({ params: { page: '4' }, query: {}, path: '/page/4', name: 'HomePage' })
    const wrapper = mount(Home, mountOptions())
    expect(wrapper.vm.currentPage).toBe(4)
    expect(wrapper.findComponent({ name: 'ArticleList' }).props('page')).toBe(4)
  })

  it('currentPage 对非法页码回退为 1', () => {
    routeState.current = reactive({ params: { page: 'abc' }, query: {}, path: '/page/abc', name: 'HomePage' })
    const wrapper = mount(Home, mountOptions())
    expect(wrapper.vm.currentPage).toBe(1)
  })

  // 分页：第 1 页回到命名路由 Home，其余页跳 HomePage 并带上页码。
  it('handlePageChange 第 1 页跳 Home，其余页跳 HomePage', () => {
    const wrapper = mount(Home, mountOptions())
    wrapper.vm.handlePageChange(1)
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
    wrapper.vm.handlePageChange(7)
    expect(push).toHaveBeenCalledWith({ name: 'HomePage', params: { page: 7 } })
  })

  // ArticleList 的 page-change 事件接线到 handlePageChange。
  it('ArticleList 触发 page-change 时驱动路由跳转', async () => {
    const wrapper = mount(Home, mountOptions())
    wrapper.findComponent({ name: 'ArticleList' }).vm.$emit('page-change', 3)
    await wrapper.vm.$nextTick()
    expect(push).toHaveBeenCalledWith({ name: 'HomePage', params: { page: 3 } })
    wrapper.findComponent({ name: 'ArticleList' }).vm.$emit('page-change', 1)
    await wrapper.vm.$nextTick()
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
  })
})
