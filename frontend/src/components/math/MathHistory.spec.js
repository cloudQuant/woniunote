import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { mountOptions } from '@/test/harness'

vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), error: vi.fn() } }))
vi.mock('@/api', () => ({
  mathTrainingApi: { createRecord: vi.fn(), getRecords: vi.fn(), getSummary: vi.fn() }
}))

/**
 * el-table 桩：按 data 渲染行，并把每个 el-table-column 的作用域插槽
 * 用真实 row 调用一次，从而真正执行单元格渲染逻辑。
 */
const tableStub = {
  name: 'el-table',
  props: {
    data: { type: Array, default: () => [] },
    rowClassName: { type: [Function, String], default: '' }
  },
  render() {
    const columns = this.$slots.default ? this.$slots.default() : []
    const slotFns = columns
      .map((col) => col && col.children && col.children.default)
      .filter((fn) => typeof fn === 'function')
    return h(
      'div',
      { class: 'el-table' },
      (this.data || []).map((row, rowIndex) => {
        const cls =
          typeof this.rowClassName === 'function'
            ? this.rowClassName({ row, rowIndex })
            : this.rowClassName
        const cells = slotFns.map((fn) => h('div', { class: 'cell' }, fn({ row })))
        return h('div', { class: ['el-table__row', cls] }, cells)
      })
    )
  }
}

// el-pagination 桩：声明 update:current-page / current-change 以便断言事件转发。
const paginationStub = {
  name: 'el-pagination',
  props: ['currentPage', 'pageSize', 'total', 'layout'],
  emits: ['update:current-page', 'current-change'],
  render() {
    return h('div', { class: 'el-pagination' })
  }
}

import MathHistory from './MathHistory.vue'

const ROWS = [
  {
    created_at: '2026-01-01T10:00:00Z',
    difficulty: 1,
    total_questions: 20,
    correct_count: 18,
    wrong_count: 2,
    accuracy: 90,
    duration_seconds: 45
  },
  {
    // 只有 start_time 时走 created_at || start_time 的回退分支
    start_time: '2026-01-02T10:00:00Z',
    difficulty: 2,
    total_questions: 20,
    correct_count: 14,
    wrong_count: 6,
    accuracy: 70,
    duration_seconds: 60
  },
  {
    created_at: '2026-01-03T10:00:00Z',
    difficulty: 3,
    total_questions: 20,
    correct_count: 5,
    wrong_count: 15,
    accuracy: 25,
    duration_seconds: 125
  }
]

function mountHistory(props = {}) {
  return mount(
    MathHistory,
    mountOptions({
      props,
      stubs: { 'el-table': tableStub, 'el-pagination': paginationStub }
    })
  )
}

describe('MathHistory.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染历史记录行：时间、难度、正确/错误、正确率与用时', () => {
    const wrapper = mountHistory({ history: ROWS, historyTotal: 3, pageSize: 10 })
    const rows = wrapper.findAll('.el-table__row')
    expect(rows).toHaveLength(3)

    const first = rows[0].findAll('.cell')
    expect(first[0].text()).toContain('2026') // created_at 格式化
    expect(first[1].text()).toBe('一级')
    expect(first[2].text()).toBe('18')
    expect(first[3].text()).toBe('2')
    expect(first[4].text()).toBe('90.0%')
    expect(first[4].find('span').classes()).toContain('text-success')
    expect(first[5].text()).toBe('45s')

    const second = rows[1].findAll('.cell')
    expect(second[0].text()).toContain('2026') // 回退到 start_time
    expect(second[1].text()).toBe('二级')
    expect(second[4].text()).toBe('70.0%')
    expect(second[4].find('span').classes()).toContain('text-warning')
    expect(second[5].text()).toBe('1m')

    const third = rows[2].findAll('.cell')
    expect(third[1].text()).toBe('三级')
    expect(third[4].text()).toBe('25.0%')
    expect(third[4].find('span').classes()).toContain('text-danger')
    expect(third[5].text()).toBe('2m5s')
  })

  it('隔行样式通过 tableRowClassName 生效', () => {
    const wrapper = mountHistory({ history: ROWS, historyTotal: 3 })
    const table = wrapper.findComponent({ name: 'el-table' })
    expect(typeof table.props('rowClassName')).toBe('function')
    const rows = wrapper.findAll('.el-table__row')
    expect(rows[0].classes()).not.toContain('stripe-row')
    expect(rows[1].classes()).toContain('stripe-row')
  })

  it('无记录且非加载中时展示空态', () => {
    const wrapper = mountHistory({ history: [], historyLoading: false })
    expect(wrapper.find('.el-table').exists()).toBe(false)
    // el-empty 桩未声明 description，值以透传属性落在外层节点上
    expect(wrapper.get('.el-empty').attributes('description')).toContain('暂无训练记录')
  })

  it('加载中时不展示空态', () => {
    const wrapper = mountHistory({ history: [], historyLoading: true })
    expect(wrapper.find('.el-empty').exists()).toBe(false)
    expect(wrapper.find('.el-table').exists()).toBe(false)
  })

  it('刷新按钮抛出 refresh 并透传 loading 状态', async () => {
    const wrapper = mountHistory({ history: ROWS, historyLoading: true })
    const refreshBtn = wrapper.findComponent({ name: 'el-button' })
    expect(refreshBtn.props('loading')).toBe(true)
    await refreshBtn.vm.$emit('click')
    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })

  it('总数超过一页时渲染分页并转发翻页事件', async () => {
    const wrapper = mountHistory({
      history: ROWS,
      historyPage: 2,
      historyTotal: 25,
      pageSize: 10
    })
    const pagination = wrapper.findComponent({ name: 'el-pagination' })
    expect(pagination.props('currentPage')).toBe(2)
    expect(pagination.props('pageSize')).toBe(10)
    expect(pagination.props('total')).toBe(25)

    await pagination.vm.$emit('update:current-page', 3)
    expect(wrapper.emitted('update:historyPage')).toEqual([[3]])

    await pagination.vm.$emit('current-change', 3)
    expect(wrapper.emitted('page-change')).toEqual([[3]])
  })

  it('总数不超过一页时不渲染分页', () => {
    const wrapper = mountHistory({ history: ROWS, historyTotal: 3, pageSize: 10 })
    expect(wrapper.find('.el-pagination').exists()).toBe(false)
  })

  it('缺省 props 时使用空数组默认值', () => {
    const wrapper = mountHistory()
    expect(wrapper.find('.el-table').exists()).toBe(false)
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })
})
