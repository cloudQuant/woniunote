<template>
  <div class="my-articles-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="我的文章" name="articles">
        <div class="page-header">
          <h3 class="page-title">我的文章</h3>
          <router-link to="/write">
            <el-button type="primary" :icon="Plus">写文章</el-button>
          </router-link>
        </div>

        <el-table :data="articles" v-loading="loading" stripe>
          <el-table-column prop="headline" label="标题" min-width="200">
            <template #default="{ row }">
              <router-link :to="{ name: 'ArticleDetail', params: { id: row.articleid } }">
                {{ row.headline }}
              </router-link>
            </template>
          </el-table-column>

          <el-table-column prop="type" label="分类" min-width="180">
            <template #default="{ row }">
              {{ getTypeName(row.type) }}
            </template>
          </el-table-column>

          <el-table-column prop="readcount" label="阅读" width="80" align="center" />
          <el-table-column prop="replycount" label="评论" width="80" align="center" />

          <el-table-column prop="drafted" label="状态" width="80" align="center">
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

          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" text @click="editArticle(row)">
                编辑
              </el-button>
              <el-popconfirm
                title="确定要删除这篇文章吗？"
                @confirm="deleteArticle(row)"
              >
                <template #reference>
                  <el-button type="danger" size="small" text>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="fetchArticles"
          />
        </div>

        <el-empty v-if="!loading && articles.length === 0" description="暂无文章" />
      </el-tab-pane>
      <el-tab-pane label="分类管理" name="categories">
        <ArticleCategoryCenter :show-header="false" article-scope="mine" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
/**
 * @component MyArticles
 * @description 我的文章管理组件
 * 展示当前登录用户的文章列表，支持分页查看。
 * 提供文章的编辑和删除功能，展示文章的状态（草稿/已发布）和统计数据（阅读/评论）。
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useArticleStore } from '@/stores/article'
import { articleApi } from '@/api'
import ArticleCategoryCenter from './ArticleCategoryCenter.vue'

const router = useRouter()
const articleStore = useArticleStore()

const activeTab = ref('articles')
const articles = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

function getTypeName(typeId) {
  return articleStore.getTypeName(typeId)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function fetchArticles() {
  loading.value = true
  try {
    const res = await articleApi.getMyList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const list = Array.isArray(res?.data) ? res.data : []
    articles.value = list
    total.value = Number(res?.total ?? list.length)
  } catch (error) {
    console.error('获取文章列表失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadArticleTypes() {
  try {
    await articleStore.fetchArticleTypes()
  } catch (error) {
    console.error('获取文章分类失败:', error)
  }
}

function editArticle(article) {
  router.push({ name: 'EditArticle', params: { id: article.articleid } })
}

async function deleteArticle(article) {
  try {
    await articleApi.delete(article.articleid)
    ElMessage.success('删除成功')
    await fetchArticles()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

onMounted(() => {
  loadArticleTypes()
  fetchArticles()
})
</script>

<style scoped>
.my-articles-page {
  padding: 10px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--wn-color-text);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
