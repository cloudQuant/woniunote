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

      <section
        v-if="pendingRecordSnapshots.length"
        class="save-outcome-alert"
        role="alert"
        aria-live="assertive"
        data-testid="pending-record-snapshots"
      >
        <h2>训练记录提交结果尚未确认</h2>
        <p>系统未自动重试。请核对历史记录；本页保留了提交快照供你查看。</p>
        <details v-for="(snapshot, index) in pendingRecordSnapshots" :key="snapshot.requestId || index">
          <summary>请求编号：{{ snapshot.requestId || '暂不可用' }} · 查看提交快照</summary>
          <p>
            {{ snapshot.payload.total_questions }} 题，正确 {{ snapshot.payload.correct_count }} 题，
            错误 {{ snapshot.payload.wrong_count }} 题，正确率 {{ snapshot.payload.accuracy }}%
          </p>
          <ul v-if="snapshot.payload.wrong_answers.length">
            <li v-for="(item, answerIndex) in snapshot.payload.wrong_answers" :key="answerIndex">
              {{ item.question }}；正确答案 {{ item.correct_answer }}；
              <template v-if="item.user_answer === null">已跳过</template>
              <template v-else>作答 {{ item.user_answer }}</template>
            </li>
          </ul>
          <p v-else>本次没有错题。</p>
        </details>
      </section>

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
            <!-- 训练进行中：答题区 -->
            <MathQuestion
              v-if="isRunning && currentQuestion"
              ref="mathQuestionRef"
              :question="currentQuestion"
              :current-index="currentIndex"
              :elapsed="currentQuestionElapsed"
              v-model:answer="answer"
              :answer-locked="answerLocked"
              :feedback="feedback"
              :progress-percent="progressPercent"
              :progress-color="progressColor"
              @submit="submitAnswer"
              @skip="skipQuestion"
            />

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
            <MathHistory
              v-model:history-page="historyPage"
              :history="history"
              :history-loading="historyLoading"
              :history-total="historyTotal"
              :page-size="pageSize"
              @refresh="loadHistory"
              @page-change="loadHistory"
            />
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @component MathTraining
 * @description 数学训练页
 * 负责页面编排：左侧训练设置与统计、右侧答题区（MathQuestion）与
 * 历史记录（MathHistory）。会话逻辑与数据加载见 composables/useMathTraining。
 */
import { ref } from 'vue'
import {
  Aim, Setting, TrendCharts, List, CircleCheck, CircleClose, DataAnalysis,
  VideoPlay, Close
} from '@element-plus/icons-vue'
import MathQuestion from '@/components/math/MathQuestion.vue'
import MathHistory from '@/components/math/MathHistory.vue'
import {
  useMathTraining,
  formatTime,
  formatDuration,
  difficultyTagType,
  tableRowClassName
} from '@/composables/useMathTraining'

// 答题区子组件引用，用于开始训练/切题后聚焦输入框
const mathQuestionRef = ref(null)

/**
 * 聚焦答题输入框（输入框渲染在 MathQuestion 子组件内）
 */
function focusAnswer() {
  mathQuestionRef.value?.focusAnswer()
}

const {
  // 状态
  difficulty, isRunning, questions, currentIndex, answer, wrongAnswers,
  correct, wrong, answerLocked, feedback, currentQuestionElapsed,
  history, historyLoading, historyPage, historyTotal, pageSize, summary,
  pendingRecordSnapshots,
  // 计算属性
  currentQuestion, progressPercent, progressColor, accuracyText,
  // 方法
  randInt, getRange, generateQuestionForOp, buildQuestions,
  startSession, endSession, submitAnswer, skipQuestion,
  loadHistory, loadSummary
} = useMathTraining({ focusAnswer })

// 暴露训练逻辑接口，供单元测试与外部调试使用
defineExpose({
  questions, wrongAnswers, pendingRecordSnapshots,
  randInt, getRange, generateQuestionForOp, buildQuestions,
  loadSummary, formatTime, formatDuration, difficultyTagType, tableRowClassName
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

.save-outcome-alert {
  margin-bottom: 20px;
  padding: 16px 20px;
  border: 1px solid var(--wn-color-warning);
  border-radius: 12px;
  background: color-mix(in srgb, var(--wn-color-warning) 12%, var(--wn-color-surface));
  color: var(--wn-color-text);
}

.save-outcome-alert h2 {
  margin: 0 0 8px;
  font-size: 16px;
}

.save-outcome-alert p {
  margin: 6px 0;
}

.save-outcome-alert details {
  margin-top: 10px;
}

.save-outcome-alert summary {
  cursor: pointer;
  font-weight: 600;
}

.save-outcome-alert ul {
  margin: 8px 0 0;
  padding-left: 22px;
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

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
