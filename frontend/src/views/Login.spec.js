import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ query: {} })
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
  wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
}

describe('Login.vue', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the login form', () => {
    const wrapper = mountLogin()
    expect(wrapper.text()).toContain('登录')
    expect(wrapper.findAllComponents({ name: 'el-input' })).toHaveLength(2)
  })

  it('logs in, toasts success and redirects to the default route', async () => {
    const wrapper = mountLogin()
    validForm(wrapper)
    await wrapper.vm.handleLogin()
    expect(login).toHaveBeenCalledWith('alice', 'secret1')
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
})
