import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Pagination from './Pagination.vue'

describe('Pagination', () => {
  it('renders nothing when there is only one page', () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 1, totalPages: 1 }
    })
    expect(wrapper.find('.pagination').exists()).toBe(false)
  })

  it('renders page links when there are multiple pages', () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 1, totalPages: 5 }
    })
    expect(wrapper.find('.pagination').exists()).toBe(true)
    // Page 1 should be marked current.
    expect(wrapper.find('.current-page').text()).toBe('1')
  })

  it('emits change with the next page when 下一页 is clicked', async () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 2, totalPages: 5 }
    })
    const links = wrapper.findAll('.page-link')
    const next = links.find((l) => l.text() === '下一页')
    await next.trigger('click')
    expect(wrapper.emitted('change')).toBeTruthy()
    expect(wrapper.emitted('change')[0]).toEqual([3])
  })

  it('does not emit change when clicking the current page', async () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 3, totalPages: 5 }
    })
    const current = wrapper.find('.current-page')
    await current.trigger('click')
    expect(wrapper.emitted('change')).toBeFalsy()
  })

  it('shows ellipsis for large page counts', () => {
    const wrapper = mount(Pagination, {
      props: { currentPage: 10, totalPages: 50, maxVisible: 5 }
    })
    expect(wrapper.text()).toContain('...')
    // First and last pages are always reachable.
    const texts = wrapper.findAll('.page-link').map((l) => l.text())
    expect(texts).toContain('1')
    expect(texts).toContain('50')
  })
})
