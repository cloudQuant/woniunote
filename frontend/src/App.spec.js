import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

// Stub the heavy child components so App renders its own layout only.
vi.mock('@/components/layout/AppHeader.vue', () => ({
  default: { name: 'AppHeader', render: () => null }
}))
vi.mock('@/components/layout/AppFooter.vue', () => ({
  default: { name: 'AppFooter', render: () => null }
}))

import App from './App.vue'

describe('App.vue', () => {
  it('renders the app shell with main content area', () => {
    const wrapper = mount(App, mountOptions({
      stubs: { 'el-config-provider': { template: '<div><slot /></div>' } }
    }))
    expect(wrapper.find('#app').exists()).toBe(true)
    expect(wrapper.find('.main-content').exists()).toBe(true)
  })
})
