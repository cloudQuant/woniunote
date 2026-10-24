<template>
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
      {{ elapsed }}s
    </div>
  </div>

  <div class="question-box">
    <div class="operation-badge" :class="'op-' + question.op">
      {{ opMap[question.op] }}
    </div>
    <div class="question-text">{{ question.display }} = ?</div>
    <div class="answer-section">
      <el-input
        ref="answerInput"
        :model-value="answer"
        @update:model-value="(value) => emit('update:answer', value)"
        size="large"
        placeholder="输入答案后按回车"
        @keyup.enter="emit('submit')"
        :disabled="answerLocked"
        class="answer-input"
        type="number"
        min="-2147483647"
        max="2147483647"
        step="any"
      />
      <div class="answer-actions">
        <el-button type="primary" size="large" @click="emit('submit')" :disabled="answerLocked">
          <el-icon><Check /></el-icon> 提交
        </el-button>
        <el-button size="large" @click="emit('skip')" :disabled="answerLocked">
          <el-icon><Right /></el-icon> 跳过
        </el-button>
      </div>
    </div>

    <transition name="fade">
      <div v-if="feedback" class="feedback-box" :class="feedback.correct ? 'correct' : 'wrong'">
        <el-icon v-if="feedback.correct"><CircleCheckFilled /></el-icon>
        <el-icon v-else><CircleCloseFilled /></el-icon>
        <span v-if="feedback.correct">正确！用时 {{ feedback.seconds }}s</span>
        <span v-else-if="feedback.userAnswer === null">
          已跳过，正确答案是 <strong>{{ feedback.correctAnswer }}</strong>
        </span>
        <span v-else>错误，正确答案是 <strong>{{ feedback.correctAnswer }}</strong></span>
      </div>
    </transition>
  </div>
</template>

<script setup>
/**
 * @component MathQuestion
 * @description 数学训练答题区组件
 * 展示当前题目、进度、计时与答题反馈；输入值与提交/跳过动作通过
 * v-model 与事件回传父级，具体会话逻辑见 composables/useMathTraining。
 */
import { ref } from 'vue'
import { Timer, Check, Right, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { opMap } from '@/composables/useMathTraining'

defineProps({
  /**
   * 当前题目对象（含 op/display）
   */
  question: {
    type: Object,
    required: true
  },
  /**
   * 当前题目序号（从 0 开始）
   */
  currentIndex: {
    type: Number,
    required: true
  },
  /**
   * 当前题目已用时（秒）
   */
  elapsed: {
    type: Number,
    default: 0
  },
  /**
   * 答案输入值（v-model:answer）
   */
  answer: {
    type: [String, Number],
    default: ''
  },
  /**
   * 是否锁定输入（反馈展示期间）
   */
  answerLocked: {
    type: Boolean,
    default: false
  },
  /**
   * 答题反馈（{ correct, correctAnswer, seconds }）
   */
  feedback: {
    type: Object,
    default: null
  },
  /**
   * 总进度百分比
   */
  progressPercent: {
    type: Number,
    default: 0
  },
  /**
   * 进度条颜色
   */
  progressColor: {
    type: String,
    default: '#409eff'
  }
})

const emit = defineEmits(['update:answer', 'submit', 'skip'])

// 答案输入框引用，暴露给父级以便切题后聚焦
const answerInput = ref(null)

/**
 * 聚焦答案输入框
 */
function focusAnswer() {
  answerInput.value?.focus()
}

defineExpose({ focusAnswer })
</script>

<style scoped>
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

@media (max-width: 768px) {
  .question-text {
    font-size: 32px;
  }

  .answer-actions {
    flex-direction: column;
  }
}
</style>
