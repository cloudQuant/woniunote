<template>
  <div class="history-section">
    <div class="history-header">
      <div class="card-header">
        <el-icon><Clock /></el-icon>
        <span>训练历史</span>
      </div>
      <el-button size="small" text type="primary" @click="emit('refresh')" :loading="historyLoading">
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
          <span :class="accuracyClass(row.accuracy)">
            {{ formatAccuracy(row.accuracy) }}%
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
        :current-page="historyPage"
        :page-size="pageSize"
        :total="historyTotal"
        layout="prev, pager, next"
        @update:current-page="emit('update:historyPage', $event)"
        @current-change="emit('page-change', $event)"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * @component MathHistory
 * @description 数学训练历史记录组件
 * 展示分页的训练记录表格；刷新与翻页动作通过事件回传父级。
 */
import { Clock, Refresh } from '@element-plus/icons-vue'
import {
  difficultyMap,
  formatTime,
  formatDuration,
  difficultyTagType,
  tableRowClassName
} from '@/composables/useMathTraining'

defineProps({
  /**
   * 历史记录列表
   */
  history: {
    type: Array,
    default: () => []
  },
  /**
   * 是否正在加载
   */
  historyLoading: {
    type: Boolean,
    default: false
  },
  /**
   * 当前页码（v-model:historyPage）
   */
  historyPage: {
    type: Number,
    default: 1
  },
  /**
   * 记录总数
   */
  historyTotal: {
    type: Number,
    default: 0
  },
  /**
   * 每页条数
   */
  pageSize: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits(['refresh', 'update:historyPage', 'page-change'])

/**
 * 格式化正确率。后端契约恒为数值（DDL NOT NULL），此处仅作防御：
 * 缺失/非数值输入回退 '0.0'，避免 toFixed 抛错导致整表渲染失败。
 * @param {*} value - accuracy 原始值
 * @returns {string} 一位小数文本
 */
function formatAccuracy(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(1) : '0.0'
}

/**
 * 正确率颜色分级；非法输入按最低档处理。
 * @param {*} value - accuracy 原始值
 * @returns {string} 样式类名
 */
function accuracyClass(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 'text-danger'
  if (n >= 80) return 'text-success'
  if (n >= 60) return 'text-warning'
  return 'text-danger'
}
</script>

<style scoped>
/* 与训练页侧栏共用的卡片标题样式（scoped 样式不跨组件生效，需各自声明） */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--wn-color-text);
  margin-bottom: 16px;
}

.text-success { color: var(--wn-color-success) !important; }
.text-danger { color: var(--wn-color-error) !important; }
.text-warning { color: var(--wn-color-warning) !important; }

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
</style>
