import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { mountOptions } from '@/test/harness'

vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), error: vi.fn() } }))
vi.mock('@/api', () => ({
  mathTrainingApi: { createRecord: vi.fn(), getRecords: vi.fn(), getSummary: vi.fn() }
}))

// el-input 桩：暴露一个可断言的 focus()，并保留 attrs 透传（keyup.enter 依赖透传）。
const focusSpy = vi.fn()
const inputStub = {
  name: 'el-input',
  props: ['modelValue', 'disabled', 'type', 'size', 'placeholder'],
  emits: ['update:modelValue'],
  methods: { focus: focusSpy },
  render() {
    return h('div', { class: 'el-input' })
  }
}

import MathQuestion from './MathQuestion.vue'

const QUESTION = { op: '*', display: '6 × 7', answer: 42 }

function mountQ(overrides = {}) {
  return mount(
    MathQuestion,
    mountOptions({
      props: {
        question: QUESTION,
        currentIndex: 4,
        elapsed: 12,
        answer: '',
        answerLocked: false,
        feedback: null,
        progressPercent: 25,
        progressColor: '#67c23a',
        ...overrides
      },
      stubs: { 'el-input': inputStub }
    })
  )
}

function actionButtons(wrapper) {
  return wrapper.findAllComponents({ name: 'el-button' })
}

describe('MathQuestion.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染题目、运算符徽标、进度与计时', () => {
    const wrapper = mountQ()
    expect(wrapper.get('.question-text').text()).toBe('6 × 7 = ?')
    expect(wrapper.get('.operation-badge').text()).toBe('×')
    expect(wrapper.get('.operation-badge').classes()).toContain('op-*')
    expect(wrapper.get('.progress-text').text()).toContain('第 5 / 20 题')
    expect(wrapper.get('.timer-badge').text()).toContain('12s')
    // el-progress 桩未声明 percentage/color，值以透传属性落在外层节点上
    expect(wrapper.get('.el-progress').attributes('percentage')).toBe('25')
    expect(wrapper.get('.el-progress').attributes('color')).toBe('#67c23a')
  })

  it('opMap 覆盖四种运算符', () => {
    expect(mountQ({ question: { op: '+', display: '1 + 2' } }).get('.operation-badge').text()).toBe('+')
    expect(mountQ({ question: { op: '-', display: '3 - 2' } }).get('.operation-badge').text()).toBe('-')
    expect(mountQ({ question: { op: '/', display: '8 ÷ 2' } }).get('.operation-badge').text()).toBe('÷')
  })

  it('输入变化时向上抛出 update:answer', async () => {
    const wrapper = mountQ()
    await wrapper.findComponent({ name: 'el-input' }).vm.$emit('update:modelValue', '42')
    expect(wrapper.emitted('update:answer')).toEqual([['42']])
  })

  it('提交按钮与回车键触发 submit，跳过按钮触发 skip', async () => {
    const wrapper = mountQ()
    const [submitBtn, skipBtn] = actionButtons(wrapper)

    await submitBtn.vm.$emit('click')
    await wrapper.find('.el-input').trigger('keyup', { key: 'Enter' })
    expect(wrapper.emitted('submit')).toHaveLength(2)

    await skipBtn.vm.$emit('click')
    expect(wrapper.emitted('skip')).toHaveLength(1)
  })

  it('非回车按键不触发 submit', async () => {
    const wrapper = mountQ()
    await wrapper.find('.el-input').trigger('keyup', { key: 'a' })
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('答题锁定时禁用输入框与操作按钮', () => {
    const wrapper = mountQ({ answerLocked: true })
    expect(wrapper.findComponent({ name: 'el-input' }).props('disabled')).toBe(true)
    actionButtons(wrapper).forEach((btn) => expect(btn.props('disabled')).toBe(true))
  })

  it('答对时展示正确反馈', () => {
    const wrapper = mountQ({
      feedback: { correct: true, correctAnswer: 42, seconds: 3 },
      answerLocked: true
    })
    const box = wrapper.get('.feedback-box')
    expect(box.classes()).toContain('correct')
    expect(box.text()).toContain('正确！用时 3s')
  })

  it('答错时展示正确答案', () => {
    const wrapper = mountQ({
      feedback: { correct: false, correctAnswer: 42, seconds: 5 },
      answerLocked: true
    })
    const box = wrapper.get('.feedback-box')
    expect(box.classes()).toContain('wrong')
    expect(box.text()).toContain('错误，正确答案是')
    expect(box.text()).toContain('42')
  })

  it('无反馈时不渲染反馈框', () => {
    const wrapper = mountQ({ feedback: null })
    expect(wrapper.find('.feedback-box').exists()).toBe(false)
  })

  it('focusAnswer 暴露给父级并聚焦答案输入框', () => {
    const wrapper = mountQ()
    expect(wrapper.vm.focusAnswer).toBeTypeOf('function')
    wrapper.vm.focusAnswer()
    expect(focusSpy).toHaveBeenCalledTimes(1)
  })
})
