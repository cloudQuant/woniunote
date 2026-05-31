import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, replace: vi.fn(), go: vi.fn() }),
  useRoute: () => ({ params: {}, query: {}, path: '/', name: 'Home' })
}))

import NotFound from './NotFound.vue'

describe('NotFound.vue', () => {
  it('renders the 404 content', () => {
    const wrapper = mount(NotFound, mountOptions())
    expect(wrapper.text()).toContain('404')
    expect(wrapper.text()).toContain('页面未找到')
  })

  it('goHome pushes to Home route', () => {
    const wrapper = mount(NotFound, mountOptions())
    wrapper.vm.goHome()
    expect(push).toHaveBeenCalledWith({ name: 'Home' })
  })
})
