import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const push = vi.fn()
const routeState = vi.hoisted(() => ({ query: {} }))
const resolve = vi.fn((value) => ({ matched: [{}], path: new URL(value, 'http://localhost').pathname }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, resolve }),
  useRoute: () => routeState
}))

const login = vi.fn(() => Promise.resolve({ data: { user: { userid: 1 } } }))
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ login })
}))

const success = vi.fn()
const error = vi.fn()
// notifyError calls ElMessage({...}) as a function (Epic 18.1); .success/.error
// stay available for the view's own toasts.
const toast = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: Object.assign((...a) => toast(...a), {
    success: (...a) => success(...a),
    error: (...a) => error(...a)
  })
}))

import Login from './Login.vue'

function mountLogin() {
  return mount(Login, mountOptions())
}

function validForm(wrapper) {
  wrapper.vm.form.username = 'alice'
  wrapper.vm.form.password = 'secret1'
  wrapper.vm.form.captchaCode = '1234'
  wrapper.vm.captchaId = 'cap-1'
  wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
}

describe('Login.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.query = {}
    globalThis.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve({ code: 200, data: { image: 'data:image/png;base64,x', captcha_id: 'cap-1' } })
    }))
  })

  it('renders the login form', () => {
    const wrapper = mountLogin()
    expect(wrapper.text()).toContain('登录')
    expect(wrapper.findAllComponents({ name: 'el-input' })).toHaveLength(3)
  })

  it('logs in, toasts success and redirects to the default route', async () => {
    const wrapper = mountLogin()
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(login).toHaveBeenCalledWith('alice', 'secret1', 'cap-1', '1234')
    expect(success).toHaveBeenCalledWith('登录成功')
    expect(push).toHaveBeenCalledWith('/')
  })

  it('surfaces the server message when login fails with HTTP 500', async () => {
    login.mockRejectedValueOnce(
      Object.assign(new Error('服务器内部错误'), { response: { status: 500 } })
    )
    const wrapper = mountLogin()
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(toast).toHaveBeenCalledWith({
      message: '服务器内部错误',
      type: 'error',
      grouping: true
    })
    expect(wrapper.vm.loading).toBe(false)
  })

  it('falls back to the scenario message when the rejection has an empty message', async () => {
    login.mockRejectedValueOnce(new Error(''))
    const wrapper = mountLogin()
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(toast).toHaveBeenCalledWith({
      message: '登录失败',
      type: 'error',
      grouping: true
    })
    expect(push).not.toHaveBeenCalled()
  })

  it('aborts login when the form validation fails', async () => {
    const wrapper = mountLogin()
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.handleLogin()
    expect(login).not.toHaveBeenCalled()
  })

  it('returns early when the form ref is missing', async () => {
    const wrapper = mountLogin()
    wrapper.vm.formRef = null
    await wrapper.vm.handleLogin()
    expect(login).not.toHaveBeenCalled()
  })

  it('carries a safe deep link to registration and after login', async () => {
    routeState.query = { redirect: '/write?draft=1#editor' }
    const wrapper = mountLogin()
    expect(wrapper.vm.registerTarget).toEqual({
      name: 'Register', query: { redirect: '/write?draft=1#editor' }
    })
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(push).toHaveBeenCalledWith('/write?draft=1#editor')
  })

  it('refreshes a consumed captcha after failure while retaining the username', async () => {
    login.mockRejectedValueOnce(new Error('bad credentials'))
    const wrapper = mountLogin()
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(wrapper.vm.form.username).toBe('alice')
    expect(wrapper.vm.form.captchaCode).toBe('')
    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
  })

  it('blocks a valid form until a captcha id is available and retries captcha loading', async () => {
    const wrapper = mountLogin()
    await flushPromises()
    validForm(wrapper)
    wrapper.vm.captchaId = ''
    await wrapper.vm.handleLogin()

    expect(login).not.toHaveBeenCalled()
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({
      message: '验证码暂不可用，请稍后刷新重试',
      type: 'error'
    }))
    expect(globalThis.fetch).toHaveBeenCalled()
  })

  it.each([
    { code: 503, data: { captcha_id: 'cap-1', image: 'img' } },
    { code: 200, data: { image: 'img' } },
    { code: 200, data: { captcha_id: 'cap-1' } }
  ])('clears captcha state when the response is incomplete', async (payload) => {
    globalThis.fetch = vi.fn(() => Promise.resolve({ json: () => Promise.resolve(payload) }))
    const wrapper = mountLogin()
    await flushPromises()
    expect(wrapper.vm.captchaId).toBe('')
    expect(wrapper.vm.captchaImage).toBe('')
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({
      message: expect.any(String),
      type: 'error'
    }))
  })

  it('clears captcha state when fetching the captcha fails', async () => {
    globalThis.fetch = vi.fn(() => Promise.reject(new Error('offline')))
    const wrapper = mountLogin()
    await flushPromises()
    expect(wrapper.vm.captchaId).toBe('')
    expect(wrapper.vm.captchaImage).toBe('')
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({
      message: 'offline',
      type: 'error'
    }))
  })
})
