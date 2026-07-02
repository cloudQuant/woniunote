<template>
  <div class="article-category-center">
    <div v-if="showHeader" class="page-header">
      <h3 class="page-title">文章分类管理</h3>
      <el-button :icon="Refresh" @click="refreshAll" :loading="loading || refreshingTypes">
        刷新
      </el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="文章分类调整" name="articles">
        <div class="article-category-toolbar">
          <el-cascader
            v-model="typeFilter"
            :options="articleStore.categoryOptions"
            :props="categoryCascaderProps"
            placeholder="按当前分类筛选"
            clearable
            filterable
            @change="handleFilterChange"
          />
          <div class="batch-controls">
            <el-cascader
              v-model="batchTargetType"
              :options="articleStore.categoryOptions"
              :props="categoryCascaderProps"
              placeholder="目标分类"
              clearable
              filterable
            />
            <el-button
              type="primary"
              :icon="Edit"
              :disabled="selectedArticles.length === 0 || !batchTargetType"
              :loading="batchChanging"
              @click="batchChangeType"
            >
              批量修改
            </el-button>
          </div>
        </div>

        <el-table
          :data="articles"
          v-loading="loading"
          stripe
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="headline" label="标题" min-width="220">
            <template #default="{ row }">
              <router-link :to="{ name: 'ArticleDetail', params: { id: row.articleid } }">
                {{ row.headline }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="当前分类" width="140">
            <template #default="{ row }">
              {{ articleStore.getTypeName(row.type) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.drafted === 1 ? 'info' : 'success'" size="small">
                {{ row.drafted === 1 ? '草稿' : '已发布' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createtime" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.createtime) }}
            </template>
          </el-table-column>
          <el-table-column label="修改分类" width="220" fixed="right">
            <template #default="{ row }">
              <el-cascader
                :model-value="Number(row.type)"
                :options="articleStore.categoryOptions"
                :props="categoryCascaderProps"
                :disabled="isArticleChanging(row.articleid)"
                size="small"
                clearable
                filterable
                @change="(type) => changeSingleArticleType(row, type)"
              />
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="fetchArticles"
          />
        </div>

        <el-empty v-if="!loading && articles.length === 0" description="暂无文章" />
      </el-tab-pane>

      <el-tab-pane label="分类维护" name="categories">
        <ArticleCategoryManager @changed="handleCategoriesChanged" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Refresh } from '@element-plus/icons-vue'
import { adminApi } from '@/api'
import { useArticleStore } from '@/stores/article'
import ArticleCategoryManager from '@/views/admin/ArticleCategoryManager.vue'

defineProps({
  showHeader: {
    type: Boolean,
    default: true
  }
})

const articleStore = useArticleStore()

const activeTab = ref('articles')
const articles = ref([])
const selectedArticles = ref([])
const loading = ref(false)
const refreshingTypes = ref(false)
const batchChanging = ref(false)
const rowChangingIds = ref(new Set())
const typeFilter = ref(null)
const batchTargetType = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const categoryCascaderProps = {
  checkStrictly: true,
  emitPath: false
}

function normalizeType(type) {
  const nextType = Number(type)
  return Number.isFinite(nextType) && nextType > 0 ? nextType : null
}

function buildArticleParams() {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value
  }
  const filterType = normalizeType(typeFilter.value)
  if (filterType) {
    params.type = filterType
  }
  return params
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

function isArticleChanging(articleId) {
  return rowChangingIds.value.has(articleId)
}

function setArticleChanging(articleId, changing) {
  const next = new Set(rowChangingIds.value)
  if (changing) {
    next.add(articleId)
  } else {
    next.delete(articleId)
  }
  rowChangingIds.value = next
}

async function loadArticleTypes() {
  refreshingTypes.value = true
  try {
    await articleStore.refreshArticleTypes()
  } catch (error) {
    console.error('获取文章分类失败:', error)
    ElMessage.error(error.message || '获取文章分类失败')
  } finally {
    refreshingTypes.value = false
  }
}

async function fetchArticles() {
  loading.value = true
  try {
    const res = await adminApi.getArticles(buildArticleParams())
    const list = Array.isArray(res?.data) ? res.data : []
    articles.value = list
    total.value = Number(res?.total ?? list.length)
    selectedArticles.value = []
  } catch (error) {
    console.error('获取文章列表失败:', error)
    ElMessage.error(error.message || '获取文章列表失败')
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await Promise.allSettled([
    loadArticleTypes(),
    fetchArticles()
  ])
}

function handleFilterChange() {
  currentPage.value = 1
  fetchArticles()
}

function handleSelectionChange(selection) {
  selectedArticles.value = selection
}

async function changeSingleArticleType(article, type) {
  const nextType = normalizeType(type)
  if (!nextType || nextType === Number(article.type)) {
    return
  }

  const previousType = article.type
  setArticleChanging(article.articleid, true)
  try {
    await adminApi.updateArticleType(article.articleid, nextType)
    article.type = nextType
    ElMessage.success('分类已更新')
  } catch (error) {
    article.type = previousType
    ElMessage.error(error.message || '分类更新失败')
  } finally {
    setArticleChanging(article.articleid, false)
  }
}

async function batchChangeType() {
  const nextType = normalizeType(batchTargetType.value)
  if (selectedArticles.value.length === 0) {
    ElMessage.error('请选择文章')
    return
  }
  if (!nextType) {
    ElMessage.error('请选择目标分类')
    return
  }

  batchChanging.value = true
  try {
    await Promise.all(
      selectedArticles.value.map((article) => adminApi.updateArticleType(article.articleid, nextType))
    )
    ElMessage.success(`已更新 ${selectedArticles.value.length} 篇文章`)
    batchTargetType.value = null
    await fetchArticles()
  } catch (error) {
    ElMessage.error(error.message || '批量修改失败')
  } finally {
    batchChanging.value = false
  }
}

async function handleCategoriesChanged() {
  await Promise.allSettled([
    loadArticleTypes(),
    fetchArticles()
  ])
}

onMounted(refreshAll)
</script>

<style scoped>
.article-category-center {
  padding: 10px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--wn-color-text);
}

.article-category-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.batch-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.article-category-toolbar :deep(.el-cascader),
.batch-controls :deep(.el-cascader) {
  width: 220px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.article-category-center :deep(.category-manager) {
  background: transparent;
  border-radius: 0;
  box-shadow: none;
  padding: 0;
}

@media (max-width: 768px) {
  .page-header,
  .article-category-toolbar,
  .batch-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .article-category-toolbar :deep(.el-cascader),
  .batch-controls :deep(.el-cascader) {
    width: 100%;
  }
}
</style>
