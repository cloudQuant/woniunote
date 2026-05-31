import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { globalStubs } from '@/test/harness'
import AppFooter from './AppFooter.vue'

describe('AppFooter.vue', () => {
  it('renders copyright, links and contact info', () => {
    const wrapper = mount(AppFooter, { global: { stubs: globalStubs() } })
    expect(wrapper.text()).toContain('版权所有')
    expect(wrapper.text()).toContain('友情链接')
    expect(wrapper.text()).toContain('联系博主')
    // ICP record link present.
    const links = wrapper.findAll('a').map((a) => a.attributes('href'))
    expect(links.some((h) => h && h.includes('beian.miit.gov.cn'))).toBe(true)
  })
})
