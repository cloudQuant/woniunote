import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRoute: () => ({ path: '/user/articles' }),
    useRouter: () => ({ push: vi.fn() })
  }
})

import UserCenter from './UserCenter.vue'

describe('UserCenter.vue', () => {
  it('renders the layout and computes activeMenu from route path', () => {
    localStorage.setItem('user', JSON.stringify({ nickname: 'bob', credit: 50, avatar: '' }))
    localStorage.setItem('token', 'tok')
    const wrapper = mount(UserCenter, mountOptions())
    expect(wrapper.vm.activeMenu).toBe('/user/articles')
    expect(wrapper.find('.user-center-page').exists()).toBe(true)
    localStorage.clear()
  })

  it('shows category management entry below my articles for regular users', () => {
    localStorage.setItem('user', JSON.stringify({ nickname: 'bob', credit: 50, avatar: '', role: 'user' }))
    localStorage.setItem('token', 'tok')
    const wrapper = mount(UserCenter, mountOptions())
    const text = wrapper.text()
    expect(text).toContain('分类管理')
    expect(text.indexOf('我的文章')).toBeLessThan(text.indexOf('分类管理'))
    expect(text.indexOf('分类管理')).toBeLessThan(text.indexOf('我的收藏'))
    localStorage.clear()
  })
})
