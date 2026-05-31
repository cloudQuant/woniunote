<template>
  <div class="admin-dashboard">
    <div class="admin-header">
      <h1>系统管理后台</h1>
      <span class="admin-user">管理员: {{ userStore.user?.nickname }}</span>
    </div>
    
    <!-- 选项卡 -->
    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane label="数据统计" name="stats">
        <!-- 统计卡片 -->
        <div class="stats-cards">
          <div class="stat-card">
            <div class="stat-icon">📝</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.totalArticles }}</span>
              <span class="stat-label">文章总数</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">👤</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.totalUsers }}</span>
              <span class="stat-label">用户总数</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💬</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.totalComments }}</span>
              <span class="stat-label">评论总数</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📖</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.todayViews }}</span>
              <span class="stat-label">今日浏览</span>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="系统监控" name="monitor">
        <div class="monitor-section" v-loading="monitorLoading">
          <!-- 系统概览卡片 -->
          <div class="monitor-cards">
            <div class="monitor-card cpu-card">
              <div class="card-header">
                <span class="card-icon">💻</span>
                <span class="card-title">CPU</span>
              </div>
              <div class="card-body">
                <el-progress 
                  type="dashboard" 
                  :percentage="systemStatus.cpu?.percent || 0"
                  :color="getProgressColor"
                  :width="120"
                >
                  <template #default="{ percentage }">
                    <span class="percentage-value">{{ percentage }}%</span>
                  </template>
                </el-progress>
                <div class="card-details">
                  <p>物理核心: {{ systemStatus.cpu?.count_physical || '-' }}</p>
                  <p>逻辑核心: {{ systemStatus.cpu?.count_logical || '-' }}</p>
                  <p v-if="systemStatus.cpu?.freq_current">频率: {{ systemStatus.cpu.freq_current }} MHz</p>
                </div>
              </div>
            </div>
            
            <div class="monitor-card memory-card">
              <div class="card-header">
                <span class="card-icon">🧠</span>
                <span class="card-title">内存</span>
              </div>
              <div class="card-body">
                <el-progress 
                  type="dashboard" 
                  :percentage="systemStatus.memory?.percent || 0"
                  :color="getProgressColor"
                  :width="120"
                >
                  <template #default="{ percentage }">
                    <span class="percentage-value">{{ percentage }}%</span>
                  </template>
                </el-progress>
                <div class="card-details">
                  <p>已用: {{ systemStatus.memory?.used?.formatted || '-' }}</p>
                  <p>总量: {{ systemStatus.memory?.total?.formatted || '-' }}</p>
                  <p>可用: {{ systemStatus.memory?.available?.formatted || '-' }}</p>
                </div>
              </div>
            </div>
            
            <div class="monitor-card disk-card">
              <div class="card-header">
                <span class="card-icon">💾</span>
                <span class="card-title">磁盘 ({{ systemStatus.disk?.path || '/' }})</span>
              </div>
              <div class="card-body">
                <el-progress 
                  type="dashboard" 
                  :percentage="systemStatus.disk?.percent || 0"
                  :color="getProgressColor"
                  :width="120"
                >
                  <template #default="{ percentage }">
                    <span class="percentage-value">{{ percentage }}%</span>
                  </template>
                </el-progress>
                <div class="card-details">
                  <p>已用: {{ systemStatus.disk?.used?.formatted || '-' }}</p>
                  <p>总量: {{ systemStatus.disk?.total?.formatted || '-' }}</p>
                  <p>剩余: {{ systemStatus.disk?.free?.formatted || '-' }}</p>
                </div>
              </div>
            </div>
            
            <div class="monitor-card network-card">
              <div class="card-header">
                <span class="card-icon">🌐</span>
                <span class="card-title">网络</span>
              </div>
              <div class="card-body no-progress">
                <div class="network-stats">
                  <div class="network-item">
                    <span class="label">↑ 发送</span>
                    <span class="value">{{ systemStatus.network?.bytes_sent?.formatted || '-' }}</span>
                  </div>
                  <div class="network-item">
                    <span class="label">↓ 接收</span>
                    <span class="value">{{ systemStatus.network?.bytes_recv?.formatted || '-' }}</span>
                  </div>
                  <div class="network-item">
                    <span class="label">发送包</span>
                    <span class="value">{{ formatNumber(systemStatus.network?.packets_sent) }}</span>
                  </div>
                  <div class="network-item">
                    <span class="label">接收包</span>
                    <span class="value">{{ formatNumber(systemStatus.network?.packets_recv) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 系统信息 -->
          <div class="system-info-section">
            <h3>系统信息</h3>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="主机名">{{ systemInfo.hostname || '-' }}</el-descriptions-item>
              <el-descriptions-item label="操作系统">{{ systemInfo.platform }} {{ systemInfo.platform_release }}</el-descriptions-item>
              <el-descriptions-item label="架构">{{ systemInfo.architecture || '-' }}</el-descriptions-item>
              <el-descriptions-item label="Python版本">{{ systemInfo.python_version || '-' }}</el-descriptions-item>
              <el-descriptions-item label="运行时间">{{ systemStatus.uptime?.formatted || '-' }}</el-descriptions-item>
              <el-descriptions-item label="启动时间">{{ formatDateTime(systemStatus.uptime?.boot_time) }}</el-descriptions-item>
            </el-descriptions>
          </div>
          
          <!-- 当前进程信息 -->
          <div class="process-info-section">
            <h3>应用进程</h3>
            <el-descriptions :column="4" border>
              <el-descriptions-item label="PID">{{ systemStatus.process?.pid || '-' }}</el-descriptions-item>
              <el-descriptions-item label="进程名">{{ systemStatus.process?.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="CPU占用">{{ systemStatus.process?.cpu_percent || 0 }}%</el-descriptions-item>
              <el-descriptions-item label="内存占用">{{ systemStatus.process?.memory_percent || 0 }}%</el-descriptions-item>
              <el-descriptions-item label="内存使用">{{ systemStatus.process?.memory_used?.formatted || '-' }}</el-descriptions-item>
              <el-descriptions-item label="线程数">{{ systemStatus.process?.threads || '-' }}</el-descriptions-item>
              <el-descriptions-item label="启动时间" :span="2">{{ formatDateTime(systemStatus.process?.create_time) }}</el-descriptions-item>
            </el-descriptions>
          </div>
          
          <!-- 刷新按钮 -->
          <div class="refresh-section">
            <el-button type="primary" @click="fetchSystemStatus" :loading="monitorLoading">
              <el-icon><Refresh /></el-icon> 刷新监控数据
            </el-button>
            <span class="last-update" v-if="lastUpdateTime">
              最后更新: {{ lastUpdateTime }}
            </span>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="文章管理" name="articles">
    
    <!-- 文章管理 -->
    <div class="admin-section">
      <div class="section-header">
        <h2>文章管理</h2>
        <div class="section-actions">
          <el-select v-model="typeFilter" placeholder="按类型筛选" clearable style="width: 150px; margin-right: 10px;">
            <el-option v-for="(name, id) in articleTypes" :key="id" :label="name" :value="parseInt(id)" />
          </el-select>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索文章标题"
            style="width: 200px; margin-right: 10px;"
            clearable
            @keyup.enter="handleSearch"
          />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
      </div>
      
      <el-table :data="articles" stripe v-loading="loading">
        <el-table-column prop="articleid" label="ID" width="80" />
        <el-table-column prop="headline" label="标题" min-width="200">
          <template #default="{ row }">
            <router-link :to="{ name: 'ArticleDetail', params: { id: row.articleid } }" target="_blank">
              {{ row.headline }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="作者" width="120">
          <template #default="{ row }">
            {{ row.author?.nickname || '匿名' }}
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            {{ getTypeName(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="readcount" label="阅读" width="80" />
        <el-table-column label="推荐" width="80">
          <template #default="{ row }">
            <el-tag :type="row.recommended ? 'success' : 'info'" size="small">
              {{ row.recommended ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.drafted ? 'warning' : (row.hidden ? 'danger' : 'success')" size="small">
              {{ row.drafted ? '草稿' : (row.hidden ? '隐藏' : '已发布') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createtime" label="发布时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.createtime) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="toggleRecommend(row)">
              {{ row.recommended ? '取消推荐' : '推荐' }}
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchArticles"
        />
      </div>
    </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
/**
 * @component AdminDashboard
 * @description 管理员后台仪表盘组件
 * 提供系统数据统计、服务器资源监控（CPU、内存、磁盘、网络）和文章管理功能。
 * 只有管理员权限的用户可以访问此页面。
 */
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import { articleApi, systemApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

// 选项卡
const activeTab = ref('stats')

// 文章管理
const loading = ref(false)
const articles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const typeFilter = ref(null)

const stats = reactive({
  totalArticles: 0,
  totalUsers: 0,
  totalComments: 0,
  todayViews: 0
})

// 系统监控
const monitorLoading = ref(false)
const systemInfo = ref({})
const systemStatus = ref({})
const lastUpdateTime = ref('')

const articleTypes = computed(() => articleStore.articleTypes)

function getTypeName(typeId) {
  return articleStore.getTypeName(typeId) || '未分类'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function formatNumber(num) {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString()
}

// 进度条颜色
function getProgressColor(percentage) {
  if (percentage < 50) return '#67c23a'
  if (percentage < 80) return '#e6a23c'
  return '#f56c6c'
}

// 获取系统监控数据
async function fetchSystemStatus() {
  monitorLoading.value = true
  try {
    const res = await systemApi.getStatus()
    systemInfo.value = res.data.system || {}
    systemStatus.value = res.data.resources || {}
    lastUpdateTime.value = new Date().toLocaleString('zh-CN')
  } catch (error) {
    console.error('获取系统状态失败:', error)
    ElMessage.error('获取系统监控数据失败')
  } finally {
    monitorLoading.value = false
  }
}

// 切换到监控Tab时自动加载数据
watch(activeTab, (newTab) => {
  if (newTab === 'monitor' && !systemStatus.value.has_psutil) {
    fetchSystemStatus()
  }
})

async function fetchArticles() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (typeFilter.value) {
      params.type = typeFilter.value
    }
    
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    
    const res = await articleApi.getList(params)
    articles.value = res.data
    total.value = res.total
    stats.totalArticles = res.total
  } catch (error) {
    console.error('获取文章列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchArticles()
}

async function toggleRecommend(article) {
  try {
    await articleApi.toggleRecommend(article.articleid)
    article.recommended = article.recommended ? 0 : 1
    ElMessage.success('操作成功')
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function handleDelete(article) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文章「${article.headline}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    
    await articleApi.delete(article.articleid)
    ElMessage.success('删除成功')
    fetchArticles()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(async () => {
  // 检查管理员权限
  if (!userStore.isAdmin) {
    ElMessage.error('您没有管理员权限')
    router.push({ name: 'Home' })
    return
  }
  
  await articleStore.fetchArticleTypes()
  fetchArticles()
})
</script>

<style scoped>
.admin-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid var(--wn-color-primary);
}

.admin-header h1 {
  font-size: 24px;
  color: var(--wn-color-text);
  margin: 0;
}

.admin-user {
  color: var(--wn-color-text-secondary);
  font-size: 14px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: var(--wn-shadow-card);
}

.stat-icon {
  font-size: 36px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: var(--wn-color-primary);
}

.stat-label {
  font-size: 14px;
  color: var(--wn-color-text-secondary);
}

.admin-section {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  padding: 20px;
  box-shadow: var(--wn-shadow-card);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--wn-color-border);
}

.section-header h2 {
  font-size: 18px;
  margin: 0;
  color: var(--wn-color-text);
}

.section-actions {
  display: flex;
  align-items: center;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 992px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 576px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .section-actions {
    flex-wrap: wrap;
    gap: 10px;
  }
}

/* 系统监控样式 */
.admin-tabs {
  margin-bottom: 20px;
}

.monitor-section {
  min-height: 400px;
}

.monitor-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.monitor-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, var(--wn-color-primary), var(--wn-color-primary-active));
  color: var(--wn-color-on-primary);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 20px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.card-body.no-progress {
  align-items: stretch;
}

.percentage-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--wn-color-text);
}

.card-details {
  width: 100%;
  text-align: center;
}

.card-details p {
  margin: 5px 0;
  font-size: 13px;
  color: var(--wn-color-text-secondary);
}

.network-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.network-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-sm);
}

.network-item .label {
  font-size: 12px;
  color: var(--wn-color-text-muted);
  margin-bottom: 4px;
}

.network-item .value {
  font-size: 14px;
  font-weight: 600;
  color: var(--wn-color-text);
}

.system-info-section,
.process-info-section {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: var(--wn-shadow-card);
}

.system-info-section h3,
.process-info-section h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: var(--wn-color-text);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--wn-color-border);
}

.refresh-section {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 0;
}

.last-update {
  font-size: 13px;
  color: var(--wn-color-text-muted);
}

@media (max-width: 1200px) {
  .monitor-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .monitor-cards {
    grid-template-columns: 1fr;
  }
  
  .network-stats {
    grid-template-columns: 1fr;
  }
}
</style>
