/**
 * @module composables/useMathTraining
 * @description 数学训练页共享逻辑
 * 包含题目生成、训练会话流程（计时、判分、错题记录）、历史与汇总数据加载，
 * 以及训练页与子组件（题目区、历史记录表）共用的展示辅助函数。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { mathTrainingApi } from '@/api'
import { notifyError } from '@/utils/errorToast'

/** 运算符展示映射（题目区组件同样需要） */
export const opMap = { '+': '+', '-': '-', '*': '×', '/': '÷' }

/** 难度级别展示映射（历史记录表使用） */
export const difficultyMap = { 1: '一级', 2: '二级', 3: '三级' }

/**
 * 格式化时间为本地化字符串，解析失败时原样返回
 * @param {string} iso - ISO 时间字符串
 * @returns {string} 格式化后的时间文本
 */
export function formatTime(iso) {
  // 前置判空：new Date(null/undefined) 不会抛异常（null 是合法 epoch 0，
  // 会渲染成 1970 年），必须显式拦截，原 try/catch 是死代码。
  if (!iso) return '-'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('zh-CN')
}

/**
 * 格式化时长（秒 → xs / xm / xmys）
 * @param {number} seconds - 时长（秒）
 * @returns {string} 格式化后的时长文本
 */
export function formatDuration(seconds) {
  if (!seconds) return '0s'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m${s}s` : `${m}m`
}

/**
 * 难度级别 → 历史记录标签颜色
 * @param {number} d - 难度级别
 * @returns {string} el-tag type
 */
export function difficultyTagType(d) {
  if (d === 1) return 'success'
  if (d === 2) return 'warning'
  return 'danger'
}

/**
 * 历史记录表格隔行底色
 * @param {Object} param0 - el-table 行上下文
 * @returns {string} 行类名
 */
export function tableRowClassName({ rowIndex }) {
  return rowIndex % 2 === 0 ? '' : 'stripe-row'
}

/**
 * 数学训练会话逻辑
 * 管理完整的一次训练生命周期：生成题目 → 逐题作答/跳过 → 结束并上报记录。
 * @param {Object} [options]
 * @param {Function} [options.focusAnswer] - 聚焦答题输入框的回调
 *   （输入框渲染在子组件中，父级通过该回调在开始训练/切题后聚焦）
 * @returns {Object} 训练页所需的全部状态、计算属性与方法
 */
export function useMathTraining({ focusAnswer = () => {} } = {}) {
  const difficulty = ref(2)

  const isRunning = ref(false)
  const questions = ref([])
  const currentIndex = ref(0)
  const answer = ref('')
  const wrongAnswers = ref([])

  const correct = ref(0)
  const wrong = ref(0)

  const answerLocked = ref(false)
  const feedback = ref(null)

  const sessionStartTime = ref(null)
  const sessionStartMs = ref(0)
  const questionStartMs = ref(0)
  const questionTimer = ref(null)
  const currentQuestionElapsed = ref(0)

  const history = ref([])
  const historyLoading = ref(false)
  const historyPage = ref(1)
  const historyTotal = ref(0)
  const pageSize = 10

  const summary = ref(null)
  const pendingRecordSnapshots = ref([])

  const currentQuestion = computed(() => questions.value[currentIndex.value] || null)

  const progressPercent = computed(() => {
    if (!isRunning.value || questions.value.length === 0) return 0
    return Math.round((currentIndex.value / 20) * 100)
  })

  const progressColor = computed(() => {
    const p = progressPercent.value
    if (p < 30) return '#409eff'
    if (p < 70) return '#67c23a'
    return '#e6a23c'
  })

  const accuracyText = computed(() => {
    const total = correct.value + wrong.value
    if (total === 0) return '-'
    return `${Math.round((correct.value / total) * 100)}%`
  })

  /**
   * 生成 [min, max] 区间内的随机整数
   * @param {number} min - 下界（含）
   * @param {number} max - 上界（含）
   * @returns {number} 随机整数
   */
  function randInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min
  }

  /**
   * 难度级别对应的操作数区间
   * @param {number} diff - 难度级别
   * @returns {{min: number, max: number}} 操作数区间
   */
  function getRange(diff) {
    if (diff === 1) return { min: 1, max: 9 }
    if (diff === 2) return { min: 10, max: 99 }
    return { min: 100, max: 999 }
  }

  /**
   * 为指定运算符生成一道题目
   * 除法保证整除、减法保证非负、乘法按难度收紧乘数上限。
   * @param {string} op - 运算符（+ - * /）
   * @param {number} diff - 难度级别
   * @returns {Object} 题目对象（含 a/b/op/answer/display）
   */
  function generateQuestionForOp(op, diff) {
    const { min, max } = getRange(diff)

    if (op === '/') {
      const divisor = randInt(Math.max(1, Math.floor(min / 2)), max)
      const quotient = randInt(1, Math.floor(max / Math.max(1, divisor)) || 9)
      const dividend = divisor * quotient
      return {
        a: dividend,
        b: divisor,
        op,
        answer: quotient,
        display: `${dividend} ${opMap[op]} ${divisor}`
      }
    }

    let a = randInt(min, max)
    let b = randInt(min, max)

    if (op === '-') {
      if (b > a) [a, b] = [b, a]
      return { a, b, op, answer: a - b, display: `${a} ${opMap[op]} ${b}` }
    }

    if (op === '*') {
      const mMax = diff === 1 ? 9 : diff === 2 ? 20 : 50
      a = randInt(2, mMax)
      b = randInt(2, mMax)
      return { a, b, op, answer: a * b, display: `${a} ${opMap[op]} ${b}` }
    }

    return { a, b, op, answer: a + b, display: `${a} ${opMap[op]} ${b}` }
  }

  /**
   * 构建一组训练题目：加减乘除各 5 道，共 20 道，随机打乱顺序
   */
  function buildQuestions() {
    const ops = ['+', '-', '*', '/']
    const list = []
    for (const op of ops) {
      for (let i = 0; i < 5; i++) {
        list.push(generateQuestionForOp(op, difficulty.value))
      }
    }
    for (let i = list.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[list[i], list[j]] = [list[j], list[i]]
    }
    questions.value = list
  }

  /**
   * 重置一轮训练的统计数据
   */
  function resetStats() {
    correct.value = 0
    wrong.value = 0
    currentIndex.value = 0
    answer.value = ''
    feedback.value = null
    answerLocked.value = false
    wrongAnswers.value = []
  }

  function tickQuestionTimer() {
    currentQuestionElapsed.value = Math.floor((Date.now() - questionStartMs.value) / 1000)
  }

  function startQuestionTimer() {
    stopQuestionTimer()
    currentQuestionElapsed.value = 0
    questionStartMs.value = Date.now()
    questionTimer.value = setInterval(tickQuestionTimer, 250)
  }

  function stopQuestionTimer() {
    if (questionTimer.value) {
      clearInterval(questionTimer.value)
      questionTimer.value = null
    }
  }

  /**
   * 开始一轮训练
   */
  function startSession() {
    resetStats()
    buildQuestions()
    isRunning.value = true
    sessionStartTime.value = new Date()
    sessionStartMs.value = Date.now()
    startQuestionTimer()
    nextTick(() => focusAnswer())
  }

  /**
   * 结束训练并上报训练记录
   */
  async function endSession() {
    if (!isRunning.value) return
    stopQuestionTimer()

    const endTime = new Date()
    const totalMs = Date.now() - sessionStartMs.value
    const total = correct.value + wrong.value
    const acc = total === 0 ? 0 : Math.round((correct.value / total) * 10000) / 100

    const payload = {
      difficulty: difficulty.value,
      total_questions: total,
      correct_count: correct.value,
      wrong_count: wrong.value,
      accuracy: acc,
      start_time: sessionStartTime.value.toISOString(),
      end_time: endTime.toISOString(),
      duration_seconds: Math.round(totalMs / 1000),
      wrong_answers: wrongAnswers.value.map((item) => ({ ...item }))
    }

    isRunning.value = false
    answerLocked.value = false
    feedback.value = null
    answer.value = ''

    try {
      await mathTrainingApi.createRecord(payload)
      ElMessage.success('训练记录已保存')
      loadHistory()
      loadSummary()
    } catch (error) {
      const isUnknownOutcome =
        error?.response?.data?.error_code === 'WRITE_OUTCOME_UNKNOWN' || !error?.response
      if (isUnknownOutcome) {
        pendingRecordSnapshots.value.push({
          requestId: error?.response?.data?.request_id || null,
          payload: Object.freeze({
            ...payload,
            wrong_answers: Object.freeze(payload.wrong_answers.map((item) => Object.freeze({ ...item })))
          })
        })
        ElMessage.warning('训练记录提交结果尚未确认，请刷新历史记录核实；系统未自动重试。')
      } else {
        ElMessage.error('保存训练记录失败')
      }
    }
  }

  /**
   * 记录一道错题
   * @param {Object} q - 题目对象
   * @param {*} userAns - 用户作答（可能为 null）
   */
  function recordWrongAnswer(q, userAns) {
    wrongAnswers.value.push({
      question: q.display,
      correct_answer: q.answer,
      user_answer: userAns,
      operation: q.op
    })
  }

  /**
   * 处理当前题目的作答结果：展示反馈后进入下一题或结束训练
   */
  function finishCurrent(correctFlag, correctAnswerValue, elapsedSeconds, userAns) {
    feedback.value = {
      correct: correctFlag,
      correctAnswer: correctAnswerValue,
      userAnswer: userAns,
      seconds: elapsedSeconds
    }

    if (!correctFlag && currentQuestion.value) {
      recordWrongAnswer(currentQuestion.value, userAns)
    }

    answerLocked.value = true

    setTimeout(() => {
      feedback.value = null
      answerLocked.value = false
      answer.value = ''

      if (currentIndex.value >= questions.value.length - 1) {
        endSession()
        return
      }

      currentIndex.value += 1
      startQuestionTimer()
      nextTick(() => focusAnswer())
    }, 600)
  }

  /**
   * 提交当前答案
   */
  function submitAnswer() {
    if (!isRunning.value || !currentQuestion.value || answerLocked.value) return

    const rawAnswer = String(answer.value ?? '').trim()
    if (!rawAnswer) {
      ElMessage.warning('请输入答案；如需不作答请点击跳过')
      return
    }

    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - questionStartMs.value) / 1000))
    const value = Number(rawAnswer)

    if (!Number.isFinite(value) || Math.abs(value) > 2147483647) {
      ElMessage.warning('答案必须是范围内的有限数字')
      return
    }

    if (value === currentQuestion.value.answer) {
      correct.value += 1
      finishCurrent(true, currentQuestion.value.answer, elapsedSeconds, value)
    } else {
      wrong.value += 1
      finishCurrent(false, currentQuestion.value.answer, elapsedSeconds, value)
    }
  }

  /**
   * 跳过当前题目（计为错误）
   */
  function skipQuestion() {
    if (!isRunning.value || !currentQuestion.value || answerLocked.value) return
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - questionStartMs.value) / 1000))
    wrong.value += 1
    finishCurrent(false, currentQuestion.value.answer, elapsedSeconds, null)
  }

  /**
   * 加载训练历史（分页）
   */
  async function loadHistory() {
    historyLoading.value = true
    try {
      const res = await mathTrainingApi.getRecords({ page: historyPage.value, page_size: pageSize })
      history.value = res.data || []
      historyTotal.value = res.total || 0
    } catch (error) {
      notifyError(error, '获取训练历史失败')
      history.value = []
    } finally {
      historyLoading.value = false
    }
  }

  /**
   * 加载历史汇总统计
   */
  async function loadSummary() {
    try {
      const res = await mathTrainingApi.getSummary()
      summary.value = res.data || null
    } catch (error) {
      notifyError(error, '获取训练汇总失败')
      summary.value = null
    }
  }

  watch(isRunning, (v) => {
    if (!v) {
      stopQuestionTimer()
      currentQuestionElapsed.value = 0
    }
  })

  onMounted(() => {
    loadHistory()
    loadSummary()
  })

  onBeforeUnmount(() => {
    stopQuestionTimer()
  })

  return {
    // 状态
    difficulty,
    isRunning,
    questions,
    currentIndex,
    answer,
    wrongAnswers,
    correct,
    wrong,
    answerLocked,
    feedback,
    currentQuestionElapsed,
    history,
    historyLoading,
    historyPage,
    historyTotal,
    pageSize,
    summary,
    pendingRecordSnapshots,
    // 计算属性
    currentQuestion,
    progressPercent,
    progressColor,
    accuracyText,
    // 方法
    randInt,
    getRange,
    generateQuestionForOp,
    buildQuestions,
    startSession,
    endSession,
    submitAnswer,
    skipQuestion,
    loadHistory,
    loadSummary
  }
}
