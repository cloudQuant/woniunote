import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { globalStubs } from '@/test/harness'
import EmptyState from './EmptyState.vue'

describe('EmptyState.vue', () => {
  it('renders default description', () => {
    const wrapper = mount(EmptyState, { global: { stubs: globalStubs() } })
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('uses compact padding when compact prop set', () => {
    const wrapper = mount(EmptyState, {
      props: { compact: true, description: '空空如也' },
      global: { stubs: globalStubs() }
    })
    const el = wrapper.find('.empty-state')
    expect(el.attributes('style')).toContain('24px 16px')
  })

  it('uses roomy padding by default', () => {
    const wrapper = mount(EmptyState, { global: { stubs: globalStubs() } })
    expect(wrapper.find('.empty-state').attributes('style')).toContain('48px 16px')
  })

  it('renders default slot content', () => {
    const wrapper = mount(EmptyState, {
      global: { stubs: globalStubs() },
      slots: { default: '<button class="cta">操作</button>' }
    })
    expect(wrapper.find('.cta').exists()).toBe(true)
  })
})
