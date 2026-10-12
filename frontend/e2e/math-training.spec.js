import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

/**
 * E2E coverage for the "数学训练" flow (迭代 17 / Epic 17.5).
 *
 * The route is guarded (`meta.requiresAuth`), so every scenario seeds a session
 * via `loginAs`. Questions are generated client-side (random operands), so the
 * specs read the rendered question, compute the expected answer and assert the
 * real feedback / progress / stats the composable drives.
 *
 * Backend calls are mocked via support/mockApi.js; the training record POST is
 * asserted with `page.waitForRequest` so the whole session lifecycle
 * (start → answer → feedback → finish → 上报) is exercised.
 */

const HISTORY_ROWS = [
  {
    id: 11,
    created_at: '2026-01-05T09:00:00.000Z',
    difficulty: 2,
    total_questions: 20,
    correct_count: 18,
    wrong_count: 2,
    accuracy: 90,
    duration_seconds: 95
  },
  {
    id: 10,
    created_at: '2026-01-04T09:00:00.000Z',
    difficulty: 1,
    total_questions: 20,
    correct_count: 20,
    wrong_count: 0,
    accuracy: 100,
    duration_seconds: 60
  }
]

const SUMMARY = {
  total_sessions: 2,
  total_questions: 40,
  average_accuracy: 95,
  total_duration_seconds: 155,
  total_correct: 38
}

/** Install the history/summary fixtures used by the page-level assertions. */
function withHistory() {
  return {
    overrides: {
      'GET /math-training/records': { code: 200, message: 'success', data: HISTORY_ROWS, total: 2 },
      'GET /math-training/summary': { code: 200, message: 'success', data: SUMMARY }
    }
  }
}

/** Parse "12 × 34 = ?" into [12, '×', 34]. */
function parseQuestion(text) {
  const m = text.match(/^(\d+)\s*([+\-×÷])\s*(\d+)/)
  expect(m, `unparseable question: ${text}`).not.toBeNull()
  return [Number(m[1]), m[2], Number(m[3])]
}

function expectedAnswer([a, op, b]) {
  if (op === '+') return a + b
  if (op === '-') return a - b
  if (op === '×') return a * b
  return a / b
}

/**
 * Answer the question currently on screen.
 * Waits for the input to be unlocked *and* cleared, so a submission always
 * carries the value computed for the question it belongs to.
 */
async function answerCurrentQuestion(page, { correct = true } = {}) {
  const input = page.locator('.answer-input input')
  await expect(input).toBeEnabled()
  await expect(input).toHaveValue('')

  const questionText = await page.locator('.question-text').innerText()
  const expected = expectedAnswer(parseQuestion(questionText))
  const value = correct ? expected : expected + 1

  await input.fill(String(value))
  await page.locator('.answer-actions button').first().click()
  return { questionText, expected, value }
}

/** The record payload of the POST issued when a session ends. */
function waitForRecordPost(page) {
  return page.waitForRequest(
    (req) => req.method() === 'POST' && new URL(req.url()).pathname === '/api/math-training/records'
  )
}

test.describe('Math training — route guard', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page, withHistory())
  })

  test('anonymous visitor is redirected to login', async ({ page }) => {
    await page.goto('/math-training')
    await expect(page).toHaveURL(/\/login/)
    await expect(page).toHaveURL(/redirect=(\/|%2F)math-training/)
  })
})

test.describe('Math training — session flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page, withHistory())
    await loginAs(page, 'user')
  })

  test('page renders the settings, the history table and the summary', async ({ page }) => {
    await page.goto('/math-training')

    await expect(page.locator('.page-header h1')).toContainText('数学训练')
    await expect(page.locator('.start-prompt')).toBeVisible()
    await expect(page.getByRole('button', { name: '开始训练' }).first()).toBeVisible()

    // History rows come from the mocked API.
    await expect(page.locator('.history-section .el-table__row')).toHaveCount(2)
    await expect(page.locator('.history-section')).toContainText('90.0%')
    await expect(page.locator('.history-section')).toContainText('1m35s')

    // Historical summary panel.
    const summary = page.locator('.summary-section')
    await expect(summary).toContainText('总训练次数')
    await expect(summary).toContainText('2')
    await expect(summary).toContainText('95.0%')
  })

  test('starting a session shows the first question and the progress counter', async ({ page }) => {
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()

    await expect(page.locator('.question-text')).toHaveText(/^\d+\s*[+\-×÷]\s*\d+ = \?$/)
    await expect(page.locator('.progress-text')).toHaveText('第 1 / 20 题')
    await expect(page.locator('.stat-card').first()).toContainText('1/20')
    await expect(page.getByRole('button', { name: '结束训练' })).toBeVisible()
    await expect(page.locator('.answer-actions button')).toHaveText(['提交', '跳过'])
  })

  test('a correct answer shows positive feedback, updates stats and advances', async ({ page }) => {
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()
    await expect(page.locator('.progress-text')).toHaveText('第 1 / 20 题')

    await answerCurrentQuestion(page)

    const feedback = page.locator('.feedback-box')
    await expect(feedback).toBeVisible()
    await expect(feedback).toHaveClass(/correct/)
    await expect(feedback).toContainText('正确！')
    await expect(feedback).toContainText(/\d+s/)

    await expect(page.locator('.stat-card').nth(1)).toContainText('1')
    await expect(page.locator('.stat-card').nth(3)).toContainText('100%')

    // Feedback clears and the session moves to the next question.
    await expect(page.locator('.progress-text')).toHaveText('第 2 / 20 题')
    await expect(page.locator('.feedback-box')).toHaveCount(0)
  })

  test('a wrong answer reveals the correct value and is counted as an error', async ({ page }) => {
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()
    await expect(page.locator('.progress-text')).toHaveText('第 1 / 20 题')

    const { expected } = await answerCurrentQuestion(page, { correct: false })

    const feedback = page.locator('.feedback-box')
    await expect(feedback).toBeVisible()
    await expect(feedback).toHaveClass(/wrong/)
    await expect(feedback).toContainText('错误，正确答案是')
    await expect(feedback).toContainText(String(expected))

    await expect(page.locator('.stat-card').nth(2)).toContainText('1')
    await expect(page.locator('.stat-card').nth(3)).toContainText('0%')
    await expect(page.locator('.progress-text')).toHaveText('第 2 / 20 题')
  })

  test('skipping counts as a wrong answer and advances', async ({ page }) => {
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()
    await expect(page.locator('.progress-text')).toHaveText('第 1 / 20 题')

    await page.getByRole('button', { name: '跳过' }).click()

    const feedback = page.locator('.feedback-box')
    await expect(feedback).toBeVisible()
    await expect(feedback).toHaveClass(/wrong/)
    await expect(page.locator('.stat-card').nth(2)).toContainText('1')
    await expect(page.locator('.progress-text')).toHaveText('第 2 / 20 题')
  })

  test('ending a session early reports the answers collected so far', async ({ page }) => {
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()
    await expect(page.locator('.progress-text')).toHaveText('第 1 / 20 题')

    await answerCurrentQuestion(page)
    await expect(page.locator('.progress-text')).toHaveText('第 2 / 20 题')
    await answerCurrentQuestion(page, { correct: false })
    await expect(page.locator('.progress-text')).toHaveText('第 3 / 20 题')

    const requestPromise = waitForRecordPost(page)
    await page.getByRole('button', { name: '结束训练' }).click()
    const payload = (await requestPromise).postDataJSON()

    expect(payload.difficulty).toBe(2)
    expect(payload.total_questions).toBe(2)
    expect(payload.correct_count).toBe(1)
    expect(payload.wrong_count).toBe(1)
    expect(payload.accuracy).toBe(50)
    expect(payload.wrong_answers).toHaveLength(1)
    // Operands/operators are randomised per session, so only the shape is fixed.
    expect(['+', '-', '*', '/']).toContain(payload.wrong_answers[0].operation)
    expect(payload.wrong_answers[0].question).toMatch(/^\d+\s*[+\-×÷]\s*\d+$/)
    expect(typeof payload.wrong_answers[0].correct_answer).toBe('number')
    expect(typeof payload.duration_seconds).toBe('number')
    expect(Date.parse(payload.start_time)).not.toBeNaN()
    expect(Date.parse(payload.end_time)).not.toBeNaN()

    // Back to the idle state, ready for another round.
    await expect(page.locator('.start-prompt')).toBeVisible()
    await expect(page.getByRole('button', { name: '开始训练' }).first()).toBeVisible()
  })

  test('a full 20-question round reports a complete record', async ({ page }) => {
    test.setTimeout(90000)
    await page.goto('/math-training')
    await page.getByRole('button', { name: '开始训练' }).first().click()

    const requestPromise = waitForRecordPost(page)

    for (let i = 0; i < 20; i++) {
      await expect(page.locator('.progress-text')).toHaveText(`第 ${i + 1} / 20 题`)
      // Answer the first 19 correctly and deliberately miss the last one so the
      // payload carries both a correct and a wrong answer.
      await answerCurrentQuestion(page, { correct: i < 19 })
    }

    const payload = (await requestPromise).postDataJSON()
    expect(payload.total_questions).toBe(20)
    expect(payload.correct_count).toBe(19)
    expect(payload.wrong_count).toBe(1)
    expect(payload.accuracy).toBe(95)
    expect(payload.wrong_answers).toHaveLength(1)

    await expect(page.locator('.start-prompt')).toBeVisible()
    await expect(page.locator('.stats-grid')).toContainText('95%')
  })
})
