<template>
  <div class="my-credits-page">
    <h3 class="page-title">我的积分</h3>
    
    <!-- 积分汇总卡片 -->
    <div class="credit-summary" v-loading="summaryLoading">
      <div class="summary-card">
        <div class="summary-value">{{ summary.total_credit }}</div>
        <div class="summary-label">当前积分</div>
      </div>
      <div class="summary-stats">
        <div class="stat-item" v-for="(stat, key) in summary.type_stats" :key="key">
          <span class="stat-label">{{ key }}</span>
          <span class="stat-value" :class="{ positive: stat.total > 0, negative: stat.total < 0 }">
            {{ stat.total > 0 ? '+' : '' }}{{ stat.total }}
          </span>
          <span class="stat-count">({{ stat.count }}次)</span>
        </div>
      </div>
    </div>
    
    <h4 class="section-title">积分记录</h4>
    
    <div class="credits-list" v-loading="loading">
      <div 
        v-for="item in credits" 
        :key="item.creditid" 
        class="credit-item"
        :class="{ positive: item.credit > 0, negative: item.credit < 0 }"
      >
        <div class="credit-info">
          <span class="credit-category">{{ item.category }}</span>
          <span class="credit-time">{{ formatDate(item.createtime) }}</span>
        </div>
        <span class="credit-value">
          {{ item.credit > 0 ? '+' : '' }}{{ item.credit }}
        </span>
      </div>
    </div>
    
    <div class="pagination-container" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchCredits"
      />
    </div>
    
    <el-empty v-if="!loading && credits.length === 0" description="暂无积分记录" />
  </div>
</template>

<script setup>
/**
 * @component MyCredits
 * @description 我的积分记录组件
 * 展示用户的积分概览（总积分、各类型统计）和详细积分变动记录。
 * 积分记录支持分页显示，并按正负值区分颜色。
 */
import { ref, reactive, onMounted } from 'vue'
import { creditApi } from '@/api'

const credits = ref([])
const summary = reactive({
  total_credit: 0,
  type_stats: {}
})
const loading = ref(true)
const summaryLoading = ref(true)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function fetchSummary() {
  summaryLoading.value = true
  try {
    const res = await creditApi.getSummary()
    summary.total_credit = res.data.total_credit
    summary.type_stats = res.data.type_stats || {}
  } catch (error) {
    console.error('获取积分汇总失败:', error)
  } finally {
    summaryLoading.value = false
  }
}

async function fetchCredits() {
  loading.value = true
  try {
    const res = await creditApi.getList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    credits.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取积分记录失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSummary()
  fetchCredits()
})
</script>

<style scoped>
.my-credits-page {
  padding: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--wn-color-text);
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin: 25px 0 15px;
  color: var(--wn-color-text);
}

.credit-summary {
  background: linear-gradient(135deg, var(--wn-color-primary) 0%, var(--wn-color-primary-active) 100%);
  border-radius: var(--wn-radius-lg);
  padding: 25px;
  color: var(--wn-color-on-primary);
  margin-bottom: 20px;
}

.summary-card {
  text-align: center;
  margin-bottom: 20px;
}

.summary-value {
  font-size: 48px;
  font-weight: bold;
}

.summary-label {
  font-size: 14px;
  opacity: 0.9;
}

.summary-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  justify-content: center;
}

.stat-item {
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 15px;
  border-radius: 20px;
  font-size: 13px;
}

.stat-value {
  margin: 0 5px;
  font-weight: 600;
}

.stat-count {
  opacity: 0.8;
  font-size: 12px;
}

.credits-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.credit-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-md);
  border-left: 3px solid var(--wn-color-text-muted);
}

.credit-item.positive {
  border-left-color: var(--wn-color-success);
}

.credit-item.negative {
  border-left-color: var(--wn-color-error);
}

.credit-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.credit-category {
  font-size: 15px;
  font-weight: 500;
  color: var(--wn-color-text);
}

.credit-time {
  font-size: 12px;
  color: var(--wn-color-text-muted);
}

.credit-value {
  font-size: 18px;
  font-weight: bold;
  color: var(--wn-color-text-muted);
}

.credit-item.positive .credit-value {
  color: var(--wn-color-success);
}

.credit-item.negative .credit-value {
  color: var(--wn-color-error);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
