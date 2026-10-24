import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const m = vi.hoisted(() => ({
  msg: Object.assign(vi.fn(), { success: vi.fn(), warning: vi.fn(), error: vi.fn() }),
  api: {
    createRecord: vi.fn(() => Promise.resolve({})),
    getRecords: vi.fn(() => Promise.resolve({ data: [{ id: 1, difficulty: 2 }], total: 1 })),
    getSummary: vi.fn(() => Promise.resolve({ data: { total_sessions: 5, total_questions: 100, average_accuracy: 88.5, total_duration_seconds: 600, total_correct: 88 } }))
  }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/api', () => ({ mathTrainingApi: m.api }))

import MathQuestion from '@/components/math/MathQuestion.vue'
import MathHistory from '@/components/math/MathHistory.vue'
import MathTraining from './MathTraining.vue'

function mountMT() {
  return mount(MathTraining, mountOptions())
}

describe('MathTraining.vue — pure helpers', () => {
  beforeEach(() => vi.clearAllMocks())

  it('getRange returns difficulty bands', () => {
    const w = mountMT()
    expect(w.vm.getRange(1)).toEqual({ min: 1, max: 9 })
    expect(w.vm.getRange(2)).toEqual({ min: 10, max: 99 })
    expect(w.vm.getRange(3)).toEqual({ min: 100, max: 999 })
  })

  it('randInt stays within bounds', () => {
    const w = mountMT()
    for (let i = 0; i < 50; i++) {
      const n = w.vm.randInt(5, 10)
      expect(n).toBeGreaterThanOrEqual(5)
      expect(n).toBeLessThanOrEqual(10)
    }
  })

  it('generateQuestionForOp produces correct answers for every operator', () => {
    const w = mountMT()
    const add = w.vm.generateQuestionForOp('+', 2)
    expect(add.a + add.b).toBe(add.answer)
    const sub = w.vm.generateQuestionForOp('-', 2)
    expect(sub.a - sub.b).toBe(sub.answer)
    expect(sub.answer).toBeGreaterThanOrEqual(0) // never negative
    const mul = w.vm.generateQuestionForOp('*', 3)
    expect(mul.a * mul.b).toBe(mul.answer)
    const div = w.vm.generateQuestionForOp('/', 2)
    expect(div.a / div.b).toBe(div.answer)
    expect(Number.isInteger(div.answer)).toBe(true) // clean division
  })

  it('uses the selected difficulty when generating multiplication questions', () => {
    const w = mountMT()
    for (const [difficulty, maxOperand] of [[1, 9], [2, 20], [3, 50]]) {
      const question = w.vm.generateQuestionForOp('*', difficulty)
      expect(question.a).toBeGreaterThanOrEqual(2)
      expect(question.a).toBeLessThanOrEqual(maxOperand)
      expect(question.b).toBeGreaterThanOrEqual(2)
      expect(question.b).toBeLessThanOrEqual(maxOperand)
      expect(question.answer).toBe(question.a * question.b)
    }
  })

  it('buildQuestions makes 20 questions (5 per operator)', () => {
    const w = mountMT()
    w.vm.buildQuestions()
    expect(w.vm.questions.length).toBe(20)
  })

  it('formatDuration formats seconds/minutes', () => {
    const w = mountMT()
    expect(w.vm.formatDuration(0)).toBe('0s')
    expect(w.vm.formatDuration(45)).toBe('45s')
    expect(w.vm.formatDuration(60)).toBe('1m')
    expect(w.vm.formatDuration(95)).toBe('1m35s')
  })

  it('formatTime renders a localized string and tolerates bad input', () => {
    const w = mountMT()
    expect(w.vm.formatTime('2026-01-01T00:00:00Z').length).toBeGreaterThan(0)
    // 缺失输入回退占位符——null 尤其关键：new Date(null) 是合法 epoch 0，
    // 不拦截会渲染成 1970 年
    expect(w.vm.formatTime(undefined)).toBe('-')
    expect(w.vm.formatTime(null)).toBe('-')
    expect(w.vm.formatTime('')).toBe('-')
    // 非法字符串回退原值，而不是 "Invalid Date"
    expect(w.vm.formatTime('not-a-date')).toBe('not-a-date')
  })

  it('difficultyTagType maps difficulty to tag color', () => {
    const w = mountMT()
    expect(w.vm.difficultyTagType(1)).toBe('success')
    expect(w.vm.difficultyTagType(2)).toBe('warning')
    expect(w.vm.difficultyTagType(3)).toBe('danger')
  })

  it('tableRowClassName stripes odd rows', () => {
    const w = mountMT()
    expect(w.vm.tableRowClassName({ rowIndex: 0 })).toBe('')
    expect(w.vm.tableRowClassName({ rowIndex: 1 })).toBe('stripe-row')
  })

  it('accuracyText and progress computeds', async () => {
    const w = mountMT()
    expect(w.vm.accuracyText).toBe('-')
    expect(w.vm.currentQuestion).toBe(null)
    expect(w.vm.progressPercent).toBe(0)
    w.vm.correct = 3
    w.vm.wrong = 1
    await w.vm.$nextTick()
    expect(w.vm.accuracyText).toBe('75%')
  })

  it('changes progress color as a running session advances', async () => {
    const w = mountMT()
    w.vm.startSession()
    expect(w.vm.progressPercent).toBe(0)
    expect(w.vm.progressColor).toBe('#409eff')

    w.vm.currentIndex = 6
    await w.vm.$nextTick()
    expect(w.vm.progressPercent).toBe(30)
    expect(w.vm.progressColor).toBe('#67c23a')

    w.vm.currentIndex = 14
    await w.vm.$nextTick()
    expect(w.vm.progressPercent).toBe(70)
    expect(w.vm.progressColor).toBe('#e6a23c')
    w.unmount()
  })

  it('loads history and summary on mount', async () => {
    const w = mountMT()
    await flushPromises()
    expect(m.api.getRecords).toHaveBeenCalled()
    expect(m.api.getSummary).toHaveBeenCalled()
    expect(w.vm.history.length).toBe(1)
    expect(w.vm.summary.total_sessions).toBe(5)
  })

  it('loadHistory and loadSummary handle errors', async () => {
    m.api.getRecords.mockRejectedValueOnce(new Error('x'))
    m.api.getSummary.mockRejectedValueOnce(new Error('y'))
    const w = mountMT()
    await flushPromises()
    expect(w.vm.history).toEqual([])
    expect(w.vm.summary).toBe(null)
  })

  it('uses empty history and summary defaults for successful but incomplete API responses', async () => {
    m.api.getRecords.mockResolvedValueOnce({})
    m.api.getSummary.mockResolvedValueOnce({})
    const w = mountMT()
    await flushPromises()
    expect(w.vm.history).toEqual([])
    expect(w.vm.historyTotal).toBe(0)
    expect(w.vm.summary).toBe(null)
  })
})

describe('MathTraining.vue — session flow', () => {
  let wrappers = []
  function mountTracked() {
    const w = mountMT()
    wrappers.push(w)
    return w
  }
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    wrappers = []
  })
  afterEach(() => {
    // Unmount first (onBeforeUnmount clears interval timers), then drop any
    // still-pending setTimeout callbacks instead of executing them in a
    // detached state.
    wrappers.forEach((w) => w.unmount())
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('startSession initializes state and questions', () => {
    const w = mountTracked()
    w.vm.startSession()
    expect(w.vm.isRunning).toBe(true)
    expect(w.vm.questions.length).toBe(20)
    expect(w.vm.correct).toBe(0)
    expect(w.vm.wrong).toBe(0)
  })

  it('correct answer increments correct and advances', () => {
    const w = mountTracked()
    w.vm.startSession()
    const q = w.vm.currentQuestion
    w.vm.answer = String(q.answer)
    w.vm.submitAnswer()
    expect(w.vm.correct).toBe(1)
    expect(w.vm.feedback.correct).toBe(true)
    // advance after the 600ms feedback window
    vi.advanceTimersByTime(700)
    expect(w.vm.currentIndex).toBe(1)
  })

  it('wrong answer records a wrong entry', () => {
    const w = mountTracked()
    w.vm.startSession()
    const q = w.vm.currentQuestion
    w.vm.answer = String(q.answer + 1)
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(1)
    expect(w.vm.wrongAnswers.length).toBe(1)
    expect(w.vm.wrongAnswers[0].correct_answer).toBe(q.answer)
  })

  it('empty and out-of-range answers are rejected without counting as wrong', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.answer = ''
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(0)
    expect(w.vm.answerLocked).toBe(false)

    // Clearing a numeric input can surface null through a component boundary.
    w.vm.answer = null
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(0)
    expect(w.vm.answerLocked).toBe(false)

    w.vm.answer = 'abc'
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(0)
    w.vm.answer = '2147483648'
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(0)
    expect(m.msg.warning).toHaveBeenCalled()
  })

  it('wrong finite decimal answers remain numeric and are preserved', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.answer = '1.5'
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(1)
    expect(w.vm.wrongAnswers[0].user_answer).toBe(1.5)
  })

  it('skipping records null instead of a numeric zero', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.skipQuestion()
    expect(w.vm.wrongAnswers[0].user_answer).toBe(null)
    expect(w.vm.feedback.userAnswer).toBe(null)
  })

  it('submitAnswer is a no-op when locked or not running', () => {
    const w = mountTracked()
    w.vm.submitAnswer() // not running
    expect(w.vm.correct).toBe(0)
    w.vm.startSession()
    w.vm.answerLocked = true
    const before = w.vm.correct
    w.vm.answer = String(w.vm.currentQuestion.answer)
    w.vm.submitAnswer()
    expect(w.vm.correct).toBe(before)
  })

  it('skipQuestion marks wrong and advances', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.skipQuestion()
    expect(w.vm.wrong).toBe(1)
    // A repeated click during the feedback lock must not count the same item twice.
    w.vm.skipQuestion()
    expect(w.vm.wrong).toBe(1)
    expect(w.vm.wrongAnswers).toHaveLength(1)
    vi.advanceTimersByTime(700)
    expect(w.vm.currentIndex).toBe(1)
  })

  it('endSession posts a record and shows success', async () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.correct = 5
    w.vm.wrong = 2
    await w.vm.endSession()
    expect(m.api.createRecord).toHaveBeenCalled()
    const payload = m.api.createRecord.mock.calls[0][0]
    expect(payload.correct_count).toBe(5)
    expect(payload.wrong_count).toBe(2)
    expect(w.vm.isRunning).toBe(false)
  })

  it('unknown save outcome keeps the immutable snapshot and does not retry', async () => {
    m.api.createRecord.mockRejectedValueOnce({
      response: { status: 503, data: { error_code: 'WRITE_OUTCOME_UNKNOWN', request_id: 'math-req-7' } }
    })
    const w = mountTracked()
    await flushPromises()
    m.api.getRecords.mockClear()
    m.api.getSummary.mockClear()
    w.vm.startSession()
    w.vm.wrongAnswers.push({
      question: '1 / 2', correct_answer: 0, user_answer: null, operation: '/'
    })
    await w.vm.endSession()
    expect(m.api.createRecord).toHaveBeenCalledTimes(1)
    expect(m.api.getRecords).not.toHaveBeenCalled()
    expect(m.api.getSummary).not.toHaveBeenCalled()
    expect(m.msg.warning).toHaveBeenCalledWith(
      '训练记录提交结果尚未确认，请刷新历史记录核实；系统未自动重试。'
    )
    expect(w.vm.pendingRecordSnapshots).toHaveLength(1)
    const snapshot = w.vm.pendingRecordSnapshots[0]
    expect(snapshot.requestId).toBe('math-req-7')
    expect(snapshot.payload.wrong_answers[0].user_answer).toBe(null)
    expect(Object.isFrozen(snapshot.payload)).toBe(true)
    expect(Object.isFrozen(snapshot.payload.wrong_answers)).toBe(true)
    expect(Object.isFrozen(snapshot.payload.wrong_answers[0])).toBe(true)
    const alert = w.get('[data-testid="pending-record-snapshots"]')
    expect(alert.text()).toContain('math-req-7')
    expect(alert.text()).toContain('已跳过')
  })

  it('keeps an empty snapshot when a network failure has no request id', async () => {
    m.api.createRecord.mockRejectedValueOnce(new Error('connection lost'))
    const w = mountTracked()
    await flushPromises()
    m.api.getRecords.mockClear()
    m.api.getSummary.mockClear()

    w.vm.startSession()
    await w.vm.endSession()

    expect(m.api.createRecord).toHaveBeenCalledTimes(1)
    expect(m.api.getRecords).not.toHaveBeenCalled()
    expect(m.api.getSummary).not.toHaveBeenCalled()
    expect(w.vm.pendingRecordSnapshots).toHaveLength(1)
    expect(w.vm.pendingRecordSnapshots[0].requestId).toBe(null)
    expect(w.vm.pendingRecordSnapshots[0].payload.wrong_answers).toEqual([])
    const alert = w.get('[data-testid="pending-record-snapshots"]')
    expect(alert.text()).toContain('请求编号：暂不可用')
    expect(alert.text()).toContain('本次没有错题。')
  })

  it('known save failures surface an error without keeping an unknown snapshot', async () => {
    m.api.createRecord.mockRejectedValueOnce({
      response: { status: 400, data: { error_code: 'BAD_REQUEST' } }
    })
    const w = mountTracked()
    w.vm.startSession()
    await w.vm.endSession()
    expect(m.msg.error).toHaveBeenCalledWith('保存训练记录失败')
    expect(w.vm.pendingRecordSnapshots).toHaveLength(0)
  })

  it('finishing the last question ends the session', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.currentIndex = 19 // last
    const q = w.vm.currentQuestion
    w.vm.answer = String(q.answer)
    w.vm.submitAnswer()
    vi.advanceTimersByTime(700)
    expect(w.vm.isRunning).toBe(false)
  })

  it('endSession is a no-op when not running', async () => {
    const w = mountTracked()
    await w.vm.endSession()
    expect(m.api.createRecord).not.toHaveBeenCalled()
  })

  it('difficulty radio group is two-way bound and disabled while running', async () => {
    const w = mountTracked()
    const group = w.findComponent({ name: 'el-radio-group' })
    expect(group.props('disabled')).toBe(false)
    group.vm.$emit('update:modelValue', 3)
    await w.vm.$nextTick()
    expect(w.vm.difficulty).toBe(3)

    w.vm.startSession()
    await w.vm.$nextTick()
    expect(w.findComponent({ name: 'el-radio-group' }).props('disabled')).toBe(true)
  })

  it('answer v-model from MathQuestion feeds submitAnswer', async () => {
    const w = mountTracked()
    w.vm.startSession()
    await w.vm.$nextTick()
    const question = w.findComponent(MathQuestion)
    expect(question.exists()).toBe(true)
    question.vm.$emit('update:answer', '42')
    await w.vm.$nextTick()
    expect(w.vm.answer).toBe('42')
    // submit/skip events from the child drive the same orchestration.
    question.vm.$emit('skip')
    await w.vm.$nextTick()
    expect(w.vm.wrong).toBe(1)
  })

  it('history page v-model from MathHistory reloads that page', async () => {
    const w = mountTracked()
    await flushPromises()
    m.api.getRecords.mockClear()
    const history = w.findComponent(MathHistory)
    expect(history.exists()).toBe(true)
    history.vm.$emit('update:historyPage', 3)
    await w.vm.$nextTick()
    expect(w.vm.historyPage).toBe(3)
    // MathHistory re-emits its refresh/page-change events to loadHistory.
    history.vm.$emit('refresh')
    await flushPromises()
    expect(m.api.getRecords).toHaveBeenCalledWith({ page: 3, page_size: 10 })
  })

  it('start prompt button starts a session and the running header can end it', async () => {
    const w = mountTracked()
    await flushPromises()
    // No session yet → the start prompt renders the primary start button.
    const start = w.findAllComponents({ name: 'el-button' }).find((b) => b.text().includes('开始训练'))
    expect(start).toBeTruthy()
    start.vm.$emit('click')
    expect(w.vm.isRunning).toBe(true)

    await w.vm.$nextTick()
    const end = w.findAllComponents({ name: 'el-button' }).find((b) => b.text().includes('结束训练'))
    expect(end).toBeTruthy()
    end.vm.$emit('click')
    await flushPromises()
    expect(w.vm.isRunning).toBe(false)
  })
})
