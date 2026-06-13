<template>
  <div class="math-training-page">
    <div class="container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1><el-icon><Aim /></el-icon> 数学训练</h1>
          <p class="subtitle">每次20题，加减乘除各5道，锻炼数字敏感性</p>
        </div>
        <div class="header-actions">
          <el-button v-if="isRunning" type="danger" @click="endSession">
            <el-icon><Close /></el-icon> 结束训练
          </el-button>
          <el-button v-if="!isRunning" type="primary" size="large" @click="startSession">
            <el-icon><VideoPlay /></el-icon> 开始训练
          </el-button>
        </div>
      </div>

      <el-row :gutter="24">
        <!-- 左侧设置面板 -->
        <el-col :span="7" :xs="24">
          <div class="sidebar-card">
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>训练设置</span>
            </div>

            <div class="setting-section">
              <div class="setting-label">难度级别</div>
              <el-radio-group v-model="difficulty" :disabled="isRunning" class="difficulty-group">
                <el-radio-button :value="1">
                  <div class="diff-btn">
                    <span class="diff-level">一级</span>
                    <span class="diff-desc">个位数</span>
                  </div>
                </el-radio-button>
                <el-radio-button :value="2">
                  <div class="diff-btn">
                    <span class="diff-level">二级</span>
                    <span class="diff-desc">两位数</span>
                  </div>
                </el-radio-button>
                <el-radio-button :value="3">
                  <div class="diff-btn">
                    <span class="diff-level">三级</span>
                    <span class="diff-desc">三位数</span>
                  </div>
                </el-radio-button>
              </el-radio-group>
            </div>

            <el-divider />

            <div class="card-header">
              <el-icon><TrendCharts /></el-icon>
              <span>本次统计</span>
            </div>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon progress-icon"><el-icon><List /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value">{{ isRunning ? `${currentIndex + 1}/20` : '-' }}</div>
                  <div class="stat-label">进度</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon correct-icon"><el-icon><CircleCheck /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value text-success">{{ correct }}</div>
                  <div class="stat-label">正确</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon wrong-icon"><el-icon><CircleClose /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value text-danger">{{ wrong }}</div>
                  <div class="stat-label">错误</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon accuracy-icon"><el-icon><Aim /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value">{{ accuracyText }}</div>
                  <div class="stat-label">正确率</div>
                </div>
              </div>
            </div>

            <!-- 训练摘要 -->
            <el-divider v-if="summary" />
            <div v-if="summary" class="summary-section">
              <div class="card-header">
                <el-icon><DataAnalysis /></el-icon>
                <span>历史统计</span>
              </div>
              <div class="summary-items">
                <div class="summary-item">
                  <span class="summary-label">总训练次数</span>
                  <span class="summary-value">{{ summary.total_sessions }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">总答题数</span>
                  <span class="summary-value">{{ summary.total_questions }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">平均正确率</span>
                  <span class="summary-value">{{ summary.average_accuracy.toFixed(1) }}%</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">累计时长</span>
                  <span class="summary-value">{{ formatDuration(summary.total_duration_seconds) }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-col>

        <!-- 右侧主区域 -->
        <el-col :span="17" :xs="24">
          <div class="main-card">
            <!-- 训练进行中 -->
            <template v-if="isRunning && currentQuestion">
              <div class="question-header">
                <div class="progress-section">
                  <el-progress
                    :percentage="progressPercent"
                    :stroke-width="12"
                    :show-text="false"
                    :color="progressColor"
                  />
                  <div class="progress-text">第 {{ currentIndex + 1 }} / 20 题</div>
                </div>
                <div class="timer-badge">
                  <el-icon><Timer /></el-icon>
                  {{ currentQuestionElapsed }}s
                </div>
              </div>

              <div class="question-box">
                <div class="operation-badge" :class="'op-' + currentQuestion.op">
                  {{ opMap[currentQuestion.op] }}
                </div>
                <div class="question-text">{{ currentQuestion.display }} = ?</div>
                <div class="answer-section">
                  <el-input
                    ref="answerInput"
                    v-model="answer"
                    size="large"
                    placeholder="输入答案后按回车"
                    @keyup.enter="submitAnswer"
                    :disabled="answerLocked"
                    class="answer-input"
                    type="number"
                  />
                  <div class="answer-actions">
                    <el-button type="primary" size="large" @click="submitAnswer" :disabled="answerLocked">
                      <el-icon><Check /></el-icon> 提交
                    </el-button>
                    <el-button size="large" @click="skipQuestion" :disabled="answerLocked">
                      <el-icon><Right /></el-icon> 跳过
                    </el-button>
                  </div>
                </div>

                <transition name="fade">
                  <div v-if="feedback" class="feedback-box" :class="feedback.correct ? 'correct' : 'wrong'">
                    <el-icon v-if="feedback.correct"><CircleCheckFilled /></el-icon>
                    <el-icon v-else><CircleCloseFilled /></el-icon>
                    <span v-if="feedback.correct">正确！用时 {{ feedback.seconds }}s</span>
                    <span v-else>错误，正确答案是 <strong>{{ feedback.correctAnswer }}</strong></span>
                  </div>
                </transition>
              </div>
            </template>

            <!-- 未开始状态 -->
            <template v-else>
              <div class="start-prompt">
                <el-icon class="prompt-icon"><Aim /></el-icon>
                <h2>准备好了吗？</h2>
                <p>每次训练包含 <strong>20道题</strong>，加减乘除各5道</p>
                <p>除法运算保证结果为整数</p>
                <el-button type="primary" size="large" @click="startSession" class="start-btn">
                  <el-icon><VideoPlay /></el-icon> 开始训练
                </el-button>
              </div>
            </template>

            <el-divider />

            <!-- 历史记录 -->
            <div class="history-section">
              <div class="history-header">
                <div class="card-header">
                  <el-icon><Clock /></el-icon>
                  <span>训练历史</span>
                </div>
                <el-button size="small" text type="primary" @click="loadHistory" :loading="historyLoading">
                  <el-icon><Refresh /></el-icon> 刷新
                </el-button>
              </div>

              <el-table 
                :data="history" 
                style="width: 100%" 
                size="small" 
                v-if="history.length > 0"
                :row-class-name="tableRowClassName"
              >
                <el-table-column prop="created_at" label="时间" width="170">
                  <template #default="{ row }">
                    {{ formatTime(row.created_at || row.start_time) }}
                  </template>
                </el-table-column>
                <el-table-column prop="difficulty" label="难度" width="100">
                  <template #default="{ row }">
                    <el-tag :type="difficultyTagType(row.difficulty)" size="small">
                      {{ difficultyMap[row.difficulty] }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="total_questions" label="题量" width="80" />
                <el-table-column prop="correct_count" label="正确" width="80">
                  <template #default="{ row }">
                    <span class="text-success">{{ row.correct_count }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="wrong_count" label="错误" width="80">
                  <template #default="{ row }">
                    <span class="text-danger">{{ row.wrong_count }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="accuracy" label="正确率" width="100">
                  <template #default="{ row }">
                    <span :class="row.accuracy >= 80 ? 'text-success' : row.accuracy >= 60 ? 'text-warning' : 'text-danger'">
                      {{ row.accuracy.toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="duration_seconds" label="用时">
                  <template #default="{ row }">
                    {{ formatDuration(row.duration_seconds) }}
                  </template>
                </el-table-column>
              </el-table>

              <el-empty v-else-if="!historyLoading" description="暂无训练记录，开始你的第一次训练吧！" />
              
              <!-- 分页 -->
              <div v-if="historyTotal > pageSize" class="pagination-wrapper">
                <el-pagination
                  v-model:current-page="historyPage"
                  :page-size="pageSize"
                  :total="historyTotal"
                  layout="prev, pager, next"
                  @current-change="loadHistory"
                />
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Aim, Setting, TrendCharts, List, CircleCheck, CircleClose, DataAnalysis,
  Timer, Check, Right, VideoPlay, Close, Clock, Refresh,
  CircleCheckFilled, CircleCloseFilled
} from '@element-plus/icons-vue'
import { mathTrainingApi } from '@/api'

const opMap = { '+': '+', '-': '-', '*': '×', '/': '÷' }
const difficultyMap = { 1: '一级', 2: '二级', 3: '三级' }

const difficulty = ref(2)
const answerInput = ref(null)

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

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function getRange(diff) {
  if (diff === 1) return { min: 1, max: 9 }
  if (diff === 2) return { min: 10, max: 99 }
  return { min: 100, max: 999 }
}

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

function startSession() {
  resetStats()
  buildQuestions()
  isRunning.value = true
  sessionStartTime.value = new Date()
  sessionStartMs.value = Date.now()
  startQuestionTimer()
  nextTick(() => answerInput.value?.focus())
}

async function endSession() {
  if (!isRunning.value) return
  stopQuestionTimer()

  const endTime = new Date()
  const totalMs = Date.now() - sessionStartMs.value
  const total = correct.value + wrong.value
  const acc = total === 0 ? 0 : (correct.value / total) * 100

  const payload = {
    difficulty: difficulty.value,
    total_questions: total,
    correct_count: correct.value,
    wrong_count: wrong.value,
    accuracy: acc,
    start_time: sessionStartTime.value.toISOString(),
    end_time: endTime.toISOString(),
    duration_seconds: Math.round(totalMs / 1000),
    wrong_answers: wrongAnswers.value
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
  } catch {
    ElMessage.error('保存训练记录失败')
  }
}

function recordWrongAnswer(q, userAns) {
  wrongAnswers.value.push({
    question: q.display,
    correct_answer: q.answer,
    user_answer: userAns,
    operation: q.op
  })
}

function finishCurrent(correctFlag, correctAnswerValue, elapsedSeconds, userAns) {
  feedback.value = {
    correct: correctFlag,
    correctAnswer: correctAnswerValue,
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
    nextTick(() => answerInput.value?.focus())
  }, 600)
}

function submitAnswer() {
  if (!isRunning.value || !currentQuestion.value || answerLocked.value) return

  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - questionStartMs.value) / 1000))
  const value = Number(answer.value)

  if (!Number.isFinite(value)) {
    wrong.value += 1
    finishCurrent(false, currentQuestion.value.answer, elapsedSeconds, null)
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

function skipQuestion() {
  if (!isRunning.value || !currentQuestion.value || answerLocked.value) return
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - questionStartMs.value) / 1000))
  wrong.value += 1
  finishCurrent(false, currentQuestion.value.answer, elapsedSeconds, null)
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await mathTrainingApi.getRecords({ page: historyPage.value, page_size: pageSize })
    history.value = res.data || []
    historyTotal.value = res.total || 0
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

async function loadSummary() {
  try {
    const res = await mathTrainingApi.getSummary()
    summary.value = res.data || null
  } catch {
    summary.value = null
  }
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function formatDuration(seconds) {
  if (!seconds) return '0s'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m${s}s` : `${m}m`
}

function difficultyTagType(d) {
  if (d === 1) return 'success'
  if (d === 2) return 'warning'
  return 'danger'
}

function tableRowClassName({ rowIndex }) {
  return rowIndex % 2 === 0 ? '' : 'stripe-row'
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
</script>

<style scoped>
.math-training-page {
  padding: 24px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 120px);
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--wn-color-text);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.subtitle {
  color: var(--wn-color-text-secondary);
  font-size: 14px;
  margin: 6px 0 0;
}

.sidebar-card,
.main-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-lg);
  box-shadow: var(--wn-shadow-card);
  padding: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--wn-color-text);
  margin-bottom: 16px;
}

.setting-section {
  margin-bottom: 8px;
}

.setting-label {
  font-size: 13px;
  color: var(--wn-color-text-secondary);
  margin-bottom: 10px;
}

.difficulty-group {
  width: 100%;
}

.difficulty-group :deep(.el-radio-button) {
  flex: 1;
}

.difficulty-group :deep(.el-radio-button__inner) {
  width: 100%;
  padding: 12px 8px;
}

.diff-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.diff-level {
  font-weight: 600;
  font-size: 14px;
}

.diff-desc {
  font-size: 11px;
  opacity: 0.8;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-lg);
  padding: 14px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.progress-icon { background: color-mix(in srgb, var(--wn-color-info) 16%, var(--wn-color-surface)); color: var(--wn-color-info); }
.correct-icon { background: color-mix(in srgb, var(--wn-color-success) 16%, var(--wn-color-surface)); color: var(--wn-color-success); }
.wrong-icon { background: color-mix(in srgb, var(--wn-color-error) 16%, var(--wn-color-surface)); color: var(--wn-color-error); }
.accuracy-icon { background: color-mix(in srgb, var(--wn-color-warning) 16%, var(--wn-color-surface)); color: var(--wn-color-warning); }

.stat-info { flex: 1; }

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--wn-color-text);
}

.stat-label {
  font-size: 12px;
  color: var(--wn-color-text-muted);
  margin-top: 2px;
}

.text-success { color: var(--wn-color-success) !important; }
.text-danger { color: var(--wn-color-error) !important; }
.text-warning { color: var(--wn-color-warning) !important; }

.summary-section { margin-top: 8px; }

.summary-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-md);
}

.summary-label {
  font-size: 13px;
  color: var(--wn-color-text-secondary);
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--wn-color-text);
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.progress-section {
  flex: 1;
}

.progress-text {
  font-size: 13px;
  color: var(--wn-color-text-secondary);
  margin-top: 8px;
  text-align: center;
}

.timer-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--wn-color-surface-soft);
  padding: 10px 16px;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 600;
  color: var(--wn-color-text-secondary);
}

.question-box {
  background: var(--wn-color-surface-soft);
  border: 2px solid var(--wn-color-border);
  border-radius: 20px;
  padding: 32px;
  position: relative;
}

.operation-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.op-\+ { background: linear-gradient(135deg, #67c23a, #85ce61); }
.op-\- { background: linear-gradient(135deg, #409eff, #66b1ff); }
.op-\* { background: linear-gradient(135deg, #e6a23c, #ebb563); }
.op-\/ { background: linear-gradient(135deg, #f56c6c, #f78989); }

.question-text {
  font-size: 48px;
  font-weight: 800;
  color: var(--wn-color-text);
  text-align: center;
  padding: 24px 0;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}

.answer-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 400px;
  margin: 0 auto;
}

.answer-input :deep(.el-input__inner) {
  font-size: 24px;
  text-align: center;
  height: 56px;
  border-radius: 12px;
}

.answer-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.answer-actions .el-button {
  flex: 1;
  height: 44px;
}

.feedback-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 20px;
}

.feedback-box.correct {
  background: color-mix(in srgb, var(--wn-color-success) 18%, var(--wn-color-surface));
  color: var(--wn-color-success);
}

.feedback-box.wrong {
  background: color-mix(in srgb, var(--wn-color-error) 18%, var(--wn-color-surface));
  color: var(--wn-color-error);
}

.feedback-box .el-icon {
  font-size: 22px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.start-prompt {
  text-align: center;
  padding: 60px 20px;
}

.prompt-icon {
  font-size: 64px;
  color: var(--wn-color-primary);
  margin-bottom: 20px;
}

.start-prompt h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--wn-color-text);
  margin: 0 0 12px;
}

.start-prompt p {
  font-size: 15px;
  color: var(--wn-color-text-secondary);
  margin: 6px 0;
}

.start-btn {
  margin-top: 24px;
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
}

.history-section { margin-top: 8px; }

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

:deep(.stripe-row) {
  background: var(--wn-color-surface-soft);
}

@media (max-width: 992px) {
  .sidebar-card {
    margin-bottom: 20px;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .question-text {
    font-size: 32px;
  }

  .answer-actions {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
