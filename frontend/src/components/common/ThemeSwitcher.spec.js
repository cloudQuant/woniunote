import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const memoryStore = (() => {
  let data = {}
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v) },
    removeItem: (k) => { delete data[k] },
    clear: () => { data = {} }
  }
})()
vi.stubGlobal('localStorage', memoryStore)

import ThemeSwitcher from './ThemeSwitcher.vue'
import { useThemeStore } from '@/stores/theme'
import { THEMES } from '@/config/themes'

// Stub Element Plus popover/icon so the panel content renders inline without
// needing the full EP teleport machinery. The popover stub keeps a name so the
// test can drive its v-model:visible handler.
const stubs = {
  'el-popover': {
    name: 'el-popover',
    emits: ['update:visible'],
    props: ['visible', 'modelValue'],
    template: '<div class="el-popover-stub"><slot name="reference" /><slot /></div>'
  },
  'el-icon': { template: '<i><slot /></i>' },
  Brush: { template: '<span />' },
  Select: { template: '<span />' }
}

describe('ThemeSwitcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.classList.remove('dark')
  })

  it('renders one cell per configured theme', () => {
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    expect(wrapper.findAll('.theme-cell').length).toBe(THEMES.length)
    expect(wrapper.findAll('.theme-group').length).toBe(2)
  })

  it('uses a keyboard-accessible trigger and exposes the selected state', () => {
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const trigger = wrapper.get('button.theme-switcher-trigger')
    const selected = wrapper.find('.theme-cell.active')

    expect(trigger.attributes('type')).toBe('button')
    expect(trigger.attributes('aria-haspopup')).toBe('dialog')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    expect(selected.attributes('aria-pressed')).toBe('true')
  })

  it('marks the current theme cell active', async () => {
    const store = useThemeStore()
    store.setTheme('notion')
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const active = wrapper.findAll('.theme-cell').filter((c) => c.classes('active'))
    expect(active.length).toBe(1)
    expect(active[0].attributes('aria-pressed')).toBe('true')
  })

  it('clicking a cell switches the theme', async () => {
    const store = useThemeStore()
    store.setTheme('claude')
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    // find the linear cell index
    const idx = THEMES.findIndex((t) => t.key === 'linear')
    await wrapper.findAll('.theme-cell')[idx].trigger('click')
    expect(store.currentTheme).toBe('linear')
    expect(document.documentElement.getAttribute('data-theme')).toBe('linear')
  })

  it('persists the selected theme to localStorage', async () => {
    const store = useThemeStore()
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const idx = THEMES.findIndex((t) => t.key === 'stripe')
    await wrapper.findAll('.theme-cell')[idx].trigger('click')
    expect(store.currentTheme).toBe('stripe')
    expect(localStorage.getItem('wn-theme')).toBe('stripe')
  })

  it('popover visibility is two-way bound (v-model:visible)', async () => {
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const popover = wrapper.findComponent({ name: 'el-popover' })
    const trigger = wrapper.get('button.theme-switcher-trigger')

    expect(trigger.attributes('aria-expanded')).toBe('false')
    popover.vm.$emit('update:visible', true)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isOpen).toBe(true)
    expect(trigger.attributes('aria-expanded')).toBe('true')

    popover.vm.$emit('update:visible', false)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isOpen).toBe(false)
  })

  it('selecting a cell closes the panel', async () => {
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    wrapper.vm.isOpen = true
    await wrapper.vm.$nextTick()
    await wrapper.findAll('.theme-cell')[0].trigger('click')
    expect(wrapper.vm.isOpen).toBe(false)
  })

  it('tolerates an unknown current theme and themes without a nav swatch', () => {
    const store = useThemeStore()
    store.themes = [
      { key: 'plain', name: '无导航色', desc: '缺少 nav 令牌', dark: false, swatch: ['#fff', '#000', '#111', '#eee'] }
    ]
    store.currentTheme = 'ghost'

    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const trigger = wrapper.get('button.theme-switcher-trigger')
    // currentMeta is undefined → the `|| ''` fallbacks render empty names.
    expect(trigger.attributes('title')).toBe('当前主题：')
    expect(trigger.attributes('aria-label')).toBe('切换主题，当前为')

    const cell = wrapper.get('.theme-cell')
    expect(cell.classes('active')).toBe(false)
    expect(cell.attributes('aria-pressed')).toBe('false')
    // previewStyle falls back to swatch[2] when the theme has no nav token.
    expect(cell.get('.theme-preview').attributes('style')).toContain('--theme-preview-nav: #111')
  })

  it('groups themes into light and dark sections', () => {
    const store = useThemeStore()
    store.themes = [
      { key: 'l1', name: '亮', desc: 'd', dark: false, swatch: ['#fff', '#000', '#111', '#eee'], nav: '#000' },
      { key: 'd1', name: '暗', desc: 'd', dark: true, swatch: ['#000', '#fff', '#eee', '#111'], nav: '#eee' }
    ]
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const groups = wrapper.findAll('.theme-group')
    expect(groups).toHaveLength(2)
    expect(groups[0].text()).toContain('明亮主题')
    expect(groups[1].text()).toContain('暗色主题')
    expect(wrapper.get('.theme-panel-count').text()).toBe('2 套')
  })
})
