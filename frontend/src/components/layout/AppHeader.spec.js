import { describe, it, expect, vi, beforeEach } from 'vitest'
import { h } from 'vue'
import fc from 'fast-check'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

const m = vi.hoisted(() => ({
  msg: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
  login: vi.fn(() => Promise.resolve({})),
  logout: vi.fn(),
  fetchArticleTypes: vi.fn(() => Promise.resolve({})),
  user: { login: null, logout: null, user: null, isLoggedIn: false, isAdmin: false },
  articleTypes: null,
  articleTypeTree: null
}))
m.user.login = m.login
m.user.logout = m.logout
const { msg, login, logout } = m

const DEFAULT_TYPES = { 1: '交易策略', 101: '股票策略', 102: '期货策略', 2: '量化框架', 201: 'vnpy' }
const DEFAULT_TREE = [
  { id: 1, name: '交易策略', children: [
    { id: 101, name: '股票策略', children: [] },
    { id: 102, name: '期货策略', children: [] }
  ] },
  { id: 2, name: '量化框架', children: [
    { id: 201, name: 'vnpy', children: [] }
  ] }
]

vi.mock('element-plus', () => ({ ElMessage: m.msg }))

vi.mock('@/stores/user', () => ({
  useUserStore: () => m.user
}))

vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({
    fetchArticleTypes: m.fetchArticleTypes,
    get articleTypes() { return m.articleTypes },
    get articleTypeTree() { return m.articleTypeTree }
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
    m.articleTypes = { ...DEFAULT_TYPES }
    m.articleTypeTree = DEFAULT_TREE
    Object.assign(m.user, { user: null, isLoggedIn: false, isAdmin: false })
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

  // Feature: ui-polish-refinement, Property 1: For any 字符串关键字 k，调用 handleSearch（注入 mock router）后：若 k.trim() 非空，则恰好发生一次跳转到 { name: 'Search', query: { keyword: k } }；若 k.trim() 为空（含纯空白、空串），则不发生任何跳转。
  it('Property 1: handleSearch pushes exactly once for non-blank keyword and never for blank', () => {
    // Mount once and reuse across runs (perf): handleSearch reads searchKeyword
    // and the module-level `push` mock, both reset per iteration.
    const wrapper = mount(AppHeader, mountOptions())
    fc.assert(
      fc.property(fc.string(), (k) => {
        push.mockClear()
        wrapper.vm.searchKeyword = k
        wrapper.vm.handleSearch()
        if (k.trim() !== '') {
          // trim 非空 → 恰好一次跳转，query.keyword 为原始（未 trim）字符串
          expect(push).toHaveBeenCalledTimes(1)
          expect(push).toHaveBeenCalledWith({ name: 'Search', query: { keyword: k } })
        } else {
          // trim 空（纯空白 / 空串）→ 不发生任何跳转
          expect(push).not.toHaveBeenCalled()
        }
      }),
      { numRuns: 100 }
    )
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

  it('handleLogin falls back to a generic message when the error has none', async () => {
    login.mockRejectedValueOnce({})
    const wrapper = mount(AppHeader, mountOptions())
    wrapper.vm.loginFormRef = { validate: (cb) => cb(true) }
    await wrapper.vm.handleLogin()
    await flushPromises()
    expect(msg.error).toHaveBeenCalledWith('登录失败')
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/captcha/generate')
  })

  it('builds the tree from the flat type map when the store has no tree', () => {
    m.articleTypeTree = []
    m.articleTypes = { 1: '交易策略', 101: '股票策略', 2: '量化框架', 201: 'vnpy', 20101: 'vnpy 子类' }
    const wrapper = mount(AppHeader, mountOptions())
    const cats = wrapper.vm.categoriesWithSubs
    expect(cats.map((c) => c.id)).toEqual([1, 2])
    expect(cats.find((c) => c.id === 1).subs.map((s) => s.id)).toEqual([101])
    // Grandchildren are flattened in order and indented by depth.
    const framework = cats.find((c) => c.id === 2)
    expect(framework.subs.map((s) => s.id)).toEqual([201, 20101])
    expect(framework.subs[1].label).toBe('　vnpy 子类')
  })

  it('yields no categories when neither tree nor type map is available', () => {
    m.articleTypeTree = []
    m.articleTypes = null
    const wrapper = mount(AppHeader, mountOptions())
    expect(wrapper.vm.categoriesWithSubs).toEqual([])
  })

  it('falls back to a generic account label when the user object is missing', () => {
    m.user.isLoggedIn = true
    m.user.user = null
    const wrapper = mount(AppHeader, mountOptions())
    expect(wrapper.get('.user-link').text()).toContain('用户')
  })

  it('tolerates tree nodes without a children array', () => {
    m.articleTypeTree = [{ id: 1, name: '无子类' }]
    const wrapper = mount(AppHeader, mountOptions())
    expect(wrapper.vm.categoriesWithSubs).toEqual([{ id: 1, name: '无子类', subs: [] }])
  })

  it('renders a plain button for leaf categories and a dropdown for parents', async () => {
    m.articleTypeTree = [
      { id: 1, name: '无子类' },
      { id: 2, name: '有子类', children: [{ id: 21, name: '子类' }] }
    ]
    const wrapper = mount(AppHeader, mountOptions())

    const button = wrapper.get('button.nav-button')
    expect(button.text()).toBe('无子类')
    await button.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'Category', params: { type: 1, page: 1 } })

    push.mockClear()
    const span = wrapper.findAll('.nav-dropdown .nav-item').find((s) => s.text() === '有子类')
    expect(span).toBeTruthy()
    await span.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'Category', params: { type: 2, page: 1 } })
  })

  it('login entry opens the modal and the dialog v-model can close it', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    await wrapper.get('button.login-link').trigger('click')
    expect(wrapper.vm.showLoginModal).toBe(true)

    const dialog = wrapper.findComponent({ name: 'el-dialog' })
    dialog.vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(wrapper.vm.showLoginModal).toBe(false)
  })

  it('login form inputs and the search box are two-way bound', async () => {
    const wrapper = mount(AppHeader, mountOptions())
    const inputs = wrapper.findAllComponents({ name: 'el-input' })
    expect(inputs).toHaveLength(4) // 3 dialog fields + mobile search bar

    inputs[0].vm.$emit('update:modelValue', 'a@b.com')
    inputs[1].vm.$emit('update:modelValue', 'secret1')
    inputs[2].vm.$emit('update:modelValue', '1234')
    inputs[3].vm.$emit('update:modelValue', 'vue')
    await flushPromises()

    expect(wrapper.vm.loginForm.username).toBe('a@b.com')
    expect(wrapper.vm.loginForm.password).toBe('secret1')
    expect(wrapper.vm.loginForm.captchaCode).toBe('1234')
    expect(wrapper.vm.searchKeyword).toBe('vue')
  })

  it('logged-in users get the account dropdown with an admin entry for admins', () => {
    m.user.isLoggedIn = true
    m.user.isAdmin = true
    m.user.user = { nickname: '管理员' }
    // The harness dropdown stub only renders the default slot; render the
    // #dropdown slot too so the menu items are inspectable.
    const dropdownStub = {
      name: 'el-dropdown',
      props: ['trigger'],
      emits: ['command'],
      render() {
        const menu = this.$slots.dropdown ? this.$slots.dropdown() : []
        return h('div', { class: 'el-dropdown' }, [this.$slots.default?.(), menu])
      }
    }
    const wrapper = mount(AppHeader, mountOptions({ stubs: { 'el-dropdown': dropdownStub } }))
    expect(wrapper.find('.login-link').exists()).toBe(false)
    expect(wrapper.get('.user-link').text()).toContain('管理员')
    expect(wrapper.text()).toContain('系统管理')
    expect(wrapper.text()).toContain('退出登录')
  })

  it('login dialog tab and close button are wired in the header slot', async () => {
    const close = vi.fn()
    const dialogStub = {
      name: 'el-dialog',
      props: ['modelValue'],
      emits: ['update:modelValue'],
      render() {
        const header = this.$slots.header ? this.$slots.header({ close }) : []
        const body = this.$slots.default ? this.$slots.default() : []
        return h('div', { class: 'el-dialog' }, [header, body])
      }
    }
    const wrapper = mount(AppHeader, mountOptions({ stubs: { 'el-dialog': dialogStub } }))

    wrapper.vm.activeTab = 'other'
    await wrapper.get('.login-tab').trigger('click')
    expect(wrapper.vm.activeTab).toBe('login')

    await wrapper.get('.login-close').trigger('click')
    expect(close).toHaveBeenCalledOnce()
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

  // --- UI semantics / accessibility (R3.1, R4.1, R11.1, R11.3) ---

  it('renders logo image with alt "云子量化"', () => {
    const wrapper = mount(AppHeader, mountOptions())
    const logo = wrapper.find('img[alt="云子量化"]')
    expect(logo.exists()).toBe(true)
    expect(logo.attributes('src')).toBe('/logo-transparent.png')
  })

  it('login entry is a <button> element (keyboard accessible)', () => {
    // userStore mock has isLoggedIn:false → the login entry renders.
    const wrapper = mount(AppHeader, mountOptions())
    const loginLink = wrapper.find('.login-link')
    expect(loginLink.exists()).toBe(true)
    expect(loginLink.element.tagName).toBe('BUTTON')
  })

  it('login modal has a single tab and no "找回密码" entry; close is an aria-labeled <button>', () => {
    // The close button + tabs live in the el-dialog #header slot. The default
    // harness el-dialog stub only renders the default slot, so provide a stub
    // that also renders the header slot (supplying the slot's `close` prop) to
    // make the "no 找回密码" and close-button assertions meaningful.
    const dialogStub = {
      name: 'el-dialog',
      props: ['modelValue'],
      render() {
        const header = this.$slots.header ? this.$slots.header({ close: () => {} }) : []
        const body = this.$slots.default ? this.$slots.default() : []
        return h('div', { class: 'el-dialog' }, [header, body])
      }
    }
    const wrapper = mount(AppHeader, mountOptions({ stubs: { 'el-dialog': dialogStub } }))

    // Exactly one login tab (登录) — the 找回密码 tab was removed.
    const tabs = wrapper.findAll('.login-tab')
    expect(tabs).toHaveLength(1)
    expect(wrapper.html()).not.toContain('找回密码')

    // Close button is a real <button aria-label="关闭"> for keyboard/SR access.
    const close = wrapper.find('.login-close')
    expect(close.exists()).toBe(true)
    expect(close.element.tagName).toBe('BUTTON')
    expect(close.attributes('aria-label')).toBe('关闭')
  })
})
