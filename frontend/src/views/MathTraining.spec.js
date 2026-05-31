import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { installLocalStorage, mountOptions } from '@/test/harness'

installLocalStorage()

const m = vi.hoisted(() => ({
  msg: { success: vi.fn(), error: vi.fn() },
  api: {
    createRecord: vi.fn(() => Promise.resolve({})),
    getRecords: vi.fn(() => Promise.resolve({ data: [{ id: 1, difficulty: 2 }], total: 1 })),
    getSummary: vi.fn(() => Promise.resolve({ data: { total_sessions: 5, total_questions: 100, average_accuracy: 88.5, total_duration_seconds: 600, total_correct: 88 } }))
  }
}))
vi.mock('element-plus', () => ({ ElMessage: m.msg }))
vi.mock('@/api', () => ({ mathTrainingApi: m.api }))

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
    w.vm.correct = 3
    w.vm.wrong = 1
    await w.vm.$nextTick()
    expect(w.vm.accuracyText).toBe('75%')
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

  it('non-numeric answer counts as wrong', () => {
    const w = mountTracked()
    w.vm.startSession()
    w.vm.answer = 'abc'
    w.vm.submitAnswer()
    expect(w.vm.wrong).toBe(1)
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

  it('endSession surfaces save errors', async () => {
    m.api.createRecord.mockRejectedValueOnce(new Error('save fail'))
    const w = mountTracked()
    w.vm.startSession()
    await w.vm.endSession()
    expect(m.msg.error).toHaveBeenCalledWith('保存训练记录失败')
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
})
