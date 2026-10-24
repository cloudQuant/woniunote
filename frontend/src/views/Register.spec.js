import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['error'])

const push = vi.fn()
const routeState = vi.hoisted(() => ({ params: {}, query: {} }))
const resolve = vi.fn((value) => ({ matched: [{}], path: new URL(value, 'http://localhost').pathname }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, resolve }),
  useRoute: () => routeState
}))

const register = vi.fn(() => Promise.resolve({ data: { userid: 1 } }))
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ register })
}))

const success = vi.fn()
const error = vi.fn()
const warning = vi.fn()
// notifyError calls ElMessage({...}) as a function (Epic 18.1); keep the
// .success/.error methods working for the existing assertions.
const toast = vi.fn()
vi.mock('element-plus', () => ({
  ElMessage: Object.assign((...a) => toast(...a), {
    success: (...a) => success(...a),
    error: (...a) => error(...a),
    warning: (...a) => warning(...a)
  })
}))

import Register from './Register.vue'

describe('Register.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params = {}
    routeState.query = {}
  })

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

  it('preserves a safe redirect through registration and login', async () => {
    routeState.query = { redirect: '/write?draft=1' }
    const wrapper = mount(Register, mountOptions())
    expect(wrapper.vm.loginTarget).toEqual({ name: 'Login', query: { redirect: '/write?draft=1' } })
    wrapper.vm.form.username = 'newuser'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(push).toHaveBeenCalledWith({ name: 'Login', query: { redirect: '/write?draft=1' } })
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

  it('surfaces the server message when registration fails with HTTP 500', async () => {
    register.mockRejectedValueOnce(
      Object.assign(new Error('服务器内部错误'), { response: { status: 500 } })
    )
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'dup'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(toast).toHaveBeenCalledWith({
      message: '服务器内部错误',
      type: 'error',
      grouping: true
    })
  })

  it('falls back to the scenario message when the rejection has an empty message', async () => {
    register.mockRejectedValueOnce(new Error(''))
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'dup'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(toast).toHaveBeenCalledWith({
      message: '注册失败',
      type: 'error',
      grouping: true
    })
  })

  it('asks the user to try login when the registration write outcome is unknown', async () => {
    register.mockRejectedValueOnce(Object.assign(new Error('write outcome unknown'), {
      errorCode: 'WRITE_OUTCOME_UNKNOWN'
    }))
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'newuser'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(warning).toHaveBeenCalledWith('注册结果暂未确认，请尝试正常登录，不要重复提交注册。')
    expect(register).toHaveBeenCalledOnce()
    expect(push).not.toHaveBeenCalled()
  })

  it.each([
    { response: { data: { error_code: 'WRITE_OUTCOME_UNKNOWN' } } },
    { response: { data: { data: { error_code: 'WRITE_OUTCOME_UNKNOWN' } } } }
  ])('recognizes WRITE_OUTCOME_UNKNOWN in backend response envelopes', async (shape) => {
    register.mockRejectedValueOnce(Object.assign(new Error('unknown result'), shape))
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'newuser'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(warning).toHaveBeenCalledWith('注册结果暂未确认，请尝试正常登录，不要重复提交注册。')
    expect(register).toHaveBeenCalledOnce()
  })

  it('binds every input through v-model', async () => {
    const wrapper = mount(Register, mountOptions())
    const inputs = wrapper.findAllComponents({ name: 'el-input' })
    expect(inputs.length).toBe(4)

    inputs[0].vm.$emit('update:modelValue', 'alice')
    inputs[1].vm.$emit('update:modelValue', 'Alice')
    inputs[2].vm.$emit('update:modelValue', 'secret1')
    inputs[3].vm.$emit('update:modelValue', 'secret1')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.form.username).toBe('alice')
    expect(wrapper.vm.form.nickname).toBe('Alice')
    expect(wrapper.vm.form.password).toBe('secret1')
    expect(wrapper.vm.form.confirmPassword).toBe('secret1')
  })

  it('submits the typed nickname when provided', async () => {
    const wrapper = mount(Register, mountOptions())
    wrapper.vm.form.username = 'newuser'
    wrapper.vm.form.nickname = 'New User'
    wrapper.vm.form.password = 'secret1'
    wrapper.vm.formRef = { validate: vi.fn(() => Promise.resolve(true)) }
    await wrapper.vm.handleRegister()
    expect(register).toHaveBeenCalledWith({
      username: 'newuser',
      nickname: 'New User',
      password: 'secret1'
    })
  })
})
