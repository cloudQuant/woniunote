import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: {}, query: {} })
}))

const register = vi.fn(() => Promise.resolve({ data: { userid: 1 } }))
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ register })
}))

const success = vi.fn()
const error = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: { success: (...a) => success(...a), error: (...a) => error(...a) }
}))

import Register from './Register.vue'

describe('Register.vue', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the registration form', () => {
    const wrapper = mount(Register, mountOptions())
    expect(wrapper.text()).toContain('注册')
  })

  it('confirm password validator rejects mismatch and accepts match', () => {
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.password = 'secret1'
    const rule = wrapper.vm.rules.confirmPassword.find((r) => r.validator)
    let mismatchErr = null
    rule.validator(null, 'different', (e) => { mismatchErr = e })
    expect(mismatchErr).toBeInstanceOf(Error)

    let matchErr = 'untouched'
    rule.validator(null, 'secret1', (e) => { matchErr = e })
    expect(matchErr).toBeUndefined()
  })

  it('handleRegister submits when form valid and redirects to Login', async () => {
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'newuser'
    wrapper.vm.form.password = 'secret1'
    // Stub the form ref validate() → valid
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(register).toHaveBeenCalledWith({
      username: 'newuser',
      nickname: 'newuser', // falls back to username
      password: 'secret1'
    })
    expect(success).toHaveBeenCalledWith('注册成功，请登录')
    expect(push).toHaveBeenCalledWith({ name: 'Login' })
  })

  it('handleRegister aborts when validation fails', async () => {
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(false)) }
    await wrapper.vm.handleRegister()
    expect(register).not.toHaveBeenCalled()
  })

  it('handleRegister returns early when formRef missing', async () => {
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.formRef = null
    await wrapper.vm.handleRegister()
    expect(register).not.toHaveBeenCalled()
  })

  it('handleRegister handles API error gracefully', async () => {
    register.mockRejectedValueOnce(new Error('username taken'))
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'dup'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(success).not.toHaveBeenCalled()
    expect(wrapper.vm.loading).toBe(false)
  })
})
