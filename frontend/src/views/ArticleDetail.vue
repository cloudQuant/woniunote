<template>
  <div class="article-detail-page">
    <div class="article-detail-container">
      <el-row :gutter="20" class="article-detail-layout">
        <el-col :span="17" :xs="24" class="article-detail-main-column">
        <div v-if="loading" class="loading-container">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="h1" style="width: 60%" />
              <div style="margin: var(--wn-space-4) 0;">
                <el-skeleton-item variant="text" style="width: 40%" />
              </div>
              <el-skeleton-item variant="text" :rows="6" />
            </template>
          </el-skeleton>
        </div>
        <div v-else class="article-container">
          <template v-if="article">
            <article class="article-content">
              <header class="article-header">
                <h1 class="article-title">{{ article.headline }}</h1>
                <div class="article-meta">
                  <span class="author">
                    <el-avatar :size="32" :src="article.author?.avatar">
                      {{ article.author?.nickname?.charAt(0) || 'U' }}
                    </el-avatar>
                    {{ article.author?.nickname || '匿名' }}
                  </span>
                  <span class="divider">|</span>
                  <span class="date">{{ formatDate(article.createtime) }}</span>
                  <span class="divider">|</span>
                  <span class="type">{{ typeName }}</span>
                  <span class="divider">|</span>
                  <span class="views"><el-icon><View /></el-icon> {{ article.readcount }}</span>
                </div>
              </header>

              <div class="article-body" ref="articleBodyRef">
                <div v-html="article.content"></div>
              </div>

              <footer class="article-footer">
                <div class="article-actions">
                  <el-button
                    :type="isFavorited ? 'warning' : 'default'"
                    @click="toggleFavorite"
                    :loading="favoriteLoading"
                  >
                    <el-icon><Star /></el-icon>
                    {{ isFavorited ? '已收藏' : '收藏' }}
                  </el-button>

                  <el-button
                    v-if="canEdit"
                    type="primary"
                    @click="editArticle"
                  >
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                </div>

                <ArticleNavigation
                  :previous-article="previousArticle"
                  :next-article="nextArticle"
                />
              </footer>
            </article>

            <!-- 评论区 -->
            <ArticleComments
              v-model:new-comment="newComment"
              v-model:reply-content="replyContent"
              :comments="comments"
              :total-comments="totalComments"
              :is-logged-in="userStore.isLoggedIn"
              :submitting-comment="submittingComment"
              :replying-to="replyingTo"
              :submitting-reply="submittingReply"
              @submit-comment="submitComment"
              @start-reply="startReply"
              @cancel-reply="cancelReply"
              @submit-reply="submitReply"
              @agree="agreeComment"
              @oppose="opposeComment"
            />
          </template>

          <el-empty v-else description="文章不存在" />
        </div>
      </el-col>
        <el-col :span="7" :xs="24" class="article-detail-sidebar-column">
          <Sidebar />
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @component ArticleDetail
 * @description 文章详情页组件
 * 展示文章内容、元数据、评论区，支持收藏、评论、点赞等交互。
 * 评论区逻辑见 composables/useArticleComments；
 * PDF 占位符替换与 MathJax 渲染见 composables/useArticleRendering。
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Star, Edit } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import { articleApi, favoriteApi } from '@/api'
import Sidebar from '@/components/sidebar/Sidebar.vue'
import ArticleComments from '@/components/article/ArticleComments.vue'
import ArticleNavigation from '@/components/article/ArticleNavigation.vue'
import { useArticleComments } from '@/composables/useArticleComments'
import { useArticleRendering } from '@/composables/useArticleRendering'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

// 状态
const article = ref(null)
const loading = ref(true)
const isFavorited = ref(false)
const favoriteLoading = ref(false)
const articleBodyRef = ref(null)

// 评论区状态与操作（渲染交给 ArticleComments 子组件）
const {
  comments, newComment, submittingComment,
  replyingTo, replyContent, submittingReply,
  totalComments,
  fetchComments, submitComment,
  startReply, cancelReply, submitReply,
  agreeComment, opposeComment
} = useArticleComments({ article })

// 正文渲染（MathJax 公式 + PDF 占位符替换）
const { renderMathFormulas, replacePdfPlaceholders, cleanupPdfViewers } = useArticleRendering(articleBodyRef)

/**
 * 文章分类名称
 */
const typeName = computed(() => {
  if (!article.value) return ''
  return articleStore.getTypeName(article.value.type)
})

/**
 * 同类型上一篇文章。旧服务未返回 navigation 时安全降级为无链接。
 */
const previousArticle = computed(() => {
  const candidate = article.value?.navigation?.previous
  return candidate?.articleid != null && candidate?.headline ? candidate : null
})

/**
 * 同类型下一篇文章。旧服务未返回 navigation 时安全降级为无链接。
 */
const nextArticle = computed(() => {
  const candidate = article.value?.navigation?.next
  return candidate?.articleid != null && candidate?.headline ? candidate : null
})

/**
 * 是否有编辑权限
 * 作者本人或编辑/管理员可编辑
 */
const canEdit = computed(() => {
  if (!userStore.isLoggedIn || !article.value) return false
  return article.value.userid === userStore.user?.userid || userStore.isEditor
})

/**
 * 格式化日期
 * @param {string} dateStr - ISO 日期字符串
 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

/**
 * 获取文章详情
 * 包括文章内容、收藏状态、评论列表
 * 并处理 PDF 占位符和 MathJax 公式
 */
async function fetchArticle() {
  loading.value = true
  try {
    const res = await articleApi.getDetail(route.params.id)
    article.value = res.data

    // 动态设置页面标题为文章标题
    if (article.value?.headline) {
      document.title = `${article.value.headline} - cloudQuant`
    }

    // 检查收藏状态
    if (userStore.isLoggedIn) {
      const favRes = await favoriteApi.check(route.params.id)
      isFavorited.value = favRes.data.is_favorited
    }

    // 获取评论
    await fetchComments()

    // 等待DOM更新后，替换PDF占位符并渲染公式
    await nextTick()
    replacePdfPlaceholders()
    renderMathFormulas()
  } catch (error) {
    console.error('获取文章详情失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 切换收藏状态
 */
async function toggleFavorite() {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }

  favoriteLoading.value = true
  try {
    if (isFavorited.value) {
      await favoriteApi.remove(article.value.articleid)
      isFavorited.value = false
      ElMessage.success('已取消收藏')
    } else {
      await favoriteApi.add(article.value.articleid)
      isFavorited.value = true
      ElMessage.success('收藏成功')
    }
  } catch (error) {
    console.error('收藏操作失败:', error)
  } finally {
    favoriteLoading.value = false
  }
}

/**
 * 跳转到编辑页面
 */
function editArticle() {
  router.push({ name: 'EditArticle', params: { id: article.value.articleid } })
}

// 监听路由参数变化，重新获取文章
watch(() => route.params.id, () => {
  if (route.params.id) {
    fetchArticle()
  }
})

onMounted(() => {
  articleStore.fetchArticleTypes()
  fetchArticle()
})

onBeforeUnmount(() => {
  // 清理PDF查看器应用实例
  cleanupPdfViewers()

  // 恢复默认标题
  document.title = 'cloudQuant'
})
</script>

<style scoped>
.article-detail-page {
  padding: 20px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.article-detail-container {
  /* 使用最大宽度容器，确保在大屏幕上布局正常 */
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.article-detail-layout {
  align-items: flex-start;
}

.article-detail-main-column {
  min-width: 0;
}

/* 桌面端把搜索与热门文章放到文章详情左侧。 */
.article-detail-sidebar-column {
  order: -1;
}

.article-container {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  padding: 30px;
}

.loading-container {
  padding: var(--wn-space-5);
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
}

.article-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--wn-color-border);
}

.article-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--wn-color-text);
  margin: 0 0 15px;
}

.article-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--wn-color-text-muted);
  font-size: 14px;
}

.author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.divider {
  color: var(--wn-color-border-strong);
}

.views {
  display: flex;
  align-items: center;
  gap: 4px;
}

.article-body {
  font-size: 16px;
  line-height: 1.8;
  color: var(--wn-color-text-secondary);
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
}

.article-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.article-body :deep(pre) {
  background: var(--wn-color-surface-soft);
  padding: 15px;
  border-radius: var(--wn-radius-sm);
  overflow-x: auto;
}

.article-body :deep(code) {
  background: var(--wn-color-surface-soft);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: Consolas, Monaco, monospace;
}

/* 表格样式 */
.article-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  max-width: 100%;
  margin: 16px 0;
  font-size: 14px;
  box-shadow: var(--wn-shadow-sm);
  border-radius: var(--wn-radius-sm);
  overflow: hidden;
  display: block;
  overflow-x: auto;
}

.article-body :deep(th),
.article-body :deep(td) {
  border: 1px solid var(--wn-color-border);
  padding: 12px 16px;
  text-align: left;
  vertical-align: top;
}

.article-body :deep(th) {
  background: var(--wn-color-surface-2);
  font-weight: 600;
  color: var(--wn-color-text);
}

.article-body :deep(tr:nth-child(even)) {
  background-color: var(--wn-color-surface-soft);
}

.article-body :deep(tr:hover) {
  background-color: var(--wn-color-surface-2);
}

.article-body :deep(td:first-child) {
  font-weight: 500;
}

.article-footer {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--wn-color-border);
}

.article-actions {
  display: flex;
  gap: 15px;
}

/* PDF查看器样式 */
.pdf-viewer-wrapper {
  margin: 20px 0;
  width: 100%;
}

/* Element Plus 的 xs 栅格在 767px 以下切换为单列。 */
@media (max-width: 767px) {
  .article-detail-container {
    padding: 0 var(--wn-space-4);
  }

  /* 小屏保留文章内容优先的阅读顺序。 */
  .article-detail-sidebar-column {
    order: initial;
    margin-top: var(--wn-space-4);
  }
}
</style>
