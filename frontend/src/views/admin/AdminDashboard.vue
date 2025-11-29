<template>
  <div class="admin-dashboard">
    <div class="admin-header">
      <h1>系统管理后台</h1>
      <span class="admin-user">管理员: {{ userStore.user?.nickname }}</span>
    </div>
    
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import { articleApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

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

const articleTypes = computed(() => articleStore.articleTypes)

function getTypeName(typeId) {
  return articleStore.getTypeName(typeId) || '未分类'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

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
  border-bottom: 2px solid #17a2b8;
}

.admin-header h1 {
  font-size: 24px;
  color: #333;
  margin: 0;
}

.admin-user {
  color: #666;
  font-size: 14px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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
  color: #17a2b8;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.admin-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.section-header h2 {
  font-size: 18px;
  margin: 0;
  color: #333;
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
</style>
