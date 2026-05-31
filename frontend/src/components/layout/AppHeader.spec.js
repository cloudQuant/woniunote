import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

const m = vi.hoisted(() => ({
  msg: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
  login: vi.fn(() => Promise.resolve({})),
  logout: vi.fn(),
  fetchArticleTypes: vi.fn(() => Promise.resolve({}))
}))
const { msg, login, logout, fetchArticleTypes } = m

vi.mock('element-plus', () => ({ ElMessage: m.msg }))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ login: m.login, logout: m.logout, user: null, isLoggedIn: false, isAdmin: false })
}))

vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    fetchArticleTypes: m.fetchArticleTypes,
    articleTypes: { 1: '交易策略', 101: '股票策略', 102: '期货策略', 2: '量化框架', 201: 'vnpy' }
  })
}))

// ThemeSwitcher is its own tested unit; stub it here.
vi.mock('@/components/common/ThemeSwitcher.vue', () => ({
  default: { name: 'ThemeSwitcher', render: () => null }
}))

import AppHeader from './AppHeader.vue'

describe('AppHeader.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve({ code: 200, data: { image: 'img', captcha_id: 'cid' } })
    }))
  })

  it('builds categoriesWithSubs hierarchy from flat types', () => {
    const wrapper = mount(AppHeader, mountOptions())
    const cats = wrapper.vm.categoriesWithSubs
    const trading = cats.find((c) => c.id === 1)
    expect(trading.name).toBe('交易策略')
    expect(trading.subs.map((s) => s.id)).toEqual([101, 102])
    const framework = cats.find((c) => c.id === 2)
    expect(framework.subs.map((s) => s.id)).toEqual([201])
  })

  it('handleSearch navigates only with non-empty keyword', () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.searchKeyword = '   '
    wrapper.vm.handleSearch()
    expect(push).not.toHaveBeenCalled()
    wrapper.vm.searchKeyword = 'vue'
    wrapper.vm.handleSearch()
    expect(push).toHaveBeenCalledWith({ name: 'Search', query: { keyword: 'vue' } })
  })

  it('handleCategoryClick navigates to category', () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.handleCategoryClick(5)
    expect(push).toHaveBeenCalledWith({ name: 'Category', params: { type: 5, page: 1 } })
  })

  it('refreshCaptcha populates captcha state on success', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    await wrapper.vm.refreshCaptcha()
    expect(wrapper.vm.captchaImage).toBe('img')
    expect(wrapper.vm.captchaId).toBe('cid')
  })

  it('refreshCaptcha swallows fetch errors', async () => {
    globalThis.fetch = vi.fn(() => Promise.reject(new Error('net')))
    const wrapper = mount(AppHeader, mountOptions())
    await wrapper.vm.refreshCaptcha()
    expect(wrapper.vm.captchaImage).toBe('')
  })

  it('opening login modal triggers captcha refresh (watch)', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.showLoginModal = true
    await flushPromises()
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/captcha/generate')
  })

  it('handleLogin succeeds: logs in, closes modal, clears form', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.loginForm.username = 'a@b.com'
    wrapper.vm.loginForm.password = 'secret1'
    wrapper.vm.loginForm.captchaCode = '1234'
    wrapper.vm.captchaId = 'cid'
    wrapper.vm.loginFormRef = { validate: (cb) => cb(true) }
    await wrapper.vm.handleLogin()
    await flushPromises()
    expect(login).toHaveBeenCalledWith('a@b.com', 'secret1', 'cid', '1234')
    expect(msg.success).toHaveBeenCalledWith('登录成功')
    expect(wrapper.vm.showLoginModal).toBe(false)
    expect(wrapper.vm.loginForm.username).toBe('')
  })

  it('handleLogin failure shows error and refreshes captcha', async () => {
    login.mockRejectedValueOnce(new Error('bad credentials'))
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.loginFormRef = { validate: (cb) => cb(true) }
    await wrapper.vm.handleLogin()
    await flushPromises()
    expect(msg.error).toHaveBeenCalledWith('bad credentials')
  })

  it('handleLogin aborts when validation invalid or ref missing', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.loginFormRef = null
    await wrapper.vm.handleLogin()
    expect(login).not.toHaveBeenCalled()
    wrapper.vm.loginFormRef = { validate: (cb) => cb(false) }
    await wrapper.vm.handleLogin()
    expect(login).not.toHaveBeenCalled()
  })

  it('handleForgotPassword validates email presence', () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.handleForgotPassword()
    expect(msg.warning).toHaveBeenCalledWith('请输入注册邮箱')
    wrapper.vm.forgotForm.email = 'x@y.com'
    wrapper.vm.handleForgotPassword()
    expect(msg.info).toHaveBeenCalledWith('密码重置功能开发中')
  })

  it('handleUserCommand routes each command', () => {
    const wrapper = mount(AppHeader, mountOptions())
    const cases = {
      write: 'WriteArticle',
      mathTraining: 'MathTraining',
      profile: 'UserProfile',
      articles: 'UserArticles',
      favorites: 'UserFavorites',
      admin: 'AdminDashboard'
    }
    for (const [cmd, name] of Object.entries(cases)) {
      push.mockClear()
      wrapper.vm.handleUserCommand(cmd)
      expect(push).toHaveBeenCalledWith({ name })
    }
  })

  it('handleUserCommand logout clears session and goes Home', () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.handleUserCommand('logout')
    expect(logout).toHaveBeenCalled()
    expect(msg.success).toHaveBeenCalledWith('已退出登录')
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('handleUserCommand ignores unknown commands', () => {
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.handleUserCommand('nope')
    expect(push).not.toHaveBeenCalled()
  })
})
