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
// needing the full EP teleport machinery.
const stubs = {
  'el-popover': {
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
  })

  it('marks the current theme cell active', async () => {
    const store = useThemeStore()
    store.setTheme('notion')
    const wrapper = mount(ThemeSwitcher, { global: { stubs } })
    const active = wrapper.findAll('.theme-cell').filter((c) => c.classes('active'))
    expect(active.length).toBe(1)
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
})
