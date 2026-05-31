/**
 * Shared test harness for mounting Vue SFCs that depend on Element Plus,
 * vue-router and Pinia. Provides:
 *   - a memory localStorage stub
 *   - global stubs for the Element Plus components used across views
 *   - helpers to build a mounting config with Pinia + a stub $router
 *
 * Element Plus components are stubbed (not really rendered) so tests stay fast
 * and deterministic while still executing the component's own <script setup>
 * logic (the part we want coverage on).
 */
import { vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { h } from 'vue'

export function installLocalStorage() {
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
  return memoryStore
}

// A permissive stub that renders its default slot inside a div. Good enough to
// execute template bindings and slot props without pulling in real EP styles.
function slotStub(name) {
  return {
    name,
    props: ['modelValue', 'data', 'row', 'type', 'icon', 'loading', 'disabled'],
    emits: ['update:modelValue', 'click', 'change', 'current-change', 'confirm', 'submit'],
    // Some components call template-ref methods (e.g. input.focus()); provide no-ops.
    methods: {
      focus() {},
      blur() {},
      validate() { return Promise.resolve(true) },
      resetFields() {},
      clearValidate() {}
    },
    render() {
      return h('div', { class: name }, this.$slots?.default ? this.$slots.default({ row: {} }) : [])
    }
  }
}

const EP_COMPONENTS = [
  'el-button', 'el-input', 'el-form', 'el-form-item', 'el-table', 'el-table-column',
  'el-tag', 'el-popconfirm', 'el-pagination', 'el-empty', 'el-card', 'el-dialog',
  'el-select', 'el-option', 'el-tabs', 'el-tab-pane', 'el-icon', 'el-avatar',
  'el-dropdown', 'el-dropdown-menu', 'el-dropdown-item', 'el-popover', 'el-tooltip',
  'el-row', 'el-col', 'el-statistic', 'el-progress', 'el-switch', 'el-radio-group',
  'el-radio', 'el-radio-button', 'el-checkbox', 'el-image', 'el-upload', 'el-badge',
  'el-divider', 'el-skeleton', 'el-skeleton-item', 'el-result', 'el-breadcrumb', 'el-breadcrumb-item',
  'el-menu', 'el-menu-item', 'el-descriptions', 'el-descriptions-item', 'el-link',
  'el-rate', 'el-tooltip', 'el-alert'
]

export function globalStubs(extra = {}) {
  const stubs = {
    'router-link': {
      props: ['to'],
      render() { return h('a', { class: 'router-link' }, this.$slots.default?.()) }
    },
    'router-view': {
      render() { return h('div', { class: 'router-view' }, this.$slots.default?.()) }
    },
    // Table columns carry scoped slots expecting a populated `row`. Rendering
    // them with a synthetic empty row throws in templates that call row.x.y().
    // We don't assert on table cell rendering, so stub the table subtree out.
    'el-table': { render() { return h('div', { class: 'el-table' }) } },
    'el-table-column': { render() { return null } }
  }
  for (const name of EP_COMPONENTS) {
    if (name === 'el-table' || name === 'el-table-column') continue
    stubs[name] = slotStub(name)
  }
  return { ...stubs, ...extra }
}

export function makePinia() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}

export function mountOptions(extra = {}) {
  const pinia = makePinia()
  return {
    global: {
      plugins: [pinia],
      stubs: globalStubs(extra.stubs),
      mocks: {
        $router: { push: vi.fn(), replace: vi.fn(), go: vi.fn() },
        $route: { params: {}, query: {}, path: '/', name: 'Home' },
        ...extra.mocks
      },
      directives: {
        loading: {} // v-loading no-op
      }
    },
    ...(extra.props ? { props: extra.props } : {})
  }
}
