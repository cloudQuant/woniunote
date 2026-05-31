<template>
  <div class="article-detail-page">
    <div class="article-detail-container">
      <el-row :gutter="20">
        <el-col :span="17" :xs="24">
        <div class="article-container" v-loading="loading">
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
              </footer>
            </article>
            
            <!-- 评论区 -->
            <section class="comment-section">
              <h3 class="section-title">评论 ({{ totalComments }})</h3>
              
              <!-- 发表评论 -->
              <div class="comment-form" v-if="userStore.isLoggedIn">
                <el-input
                  v-model="newComment"
                  type="textarea"
                  :rows="3"
                  placeholder="写下你的评论..."
                />
                <el-button 
                  type="primary" 
                  @click="submitComment" 
                  :loading="submittingComment"
                  :disabled="!newComment.trim()"
                >
                  发表评论
                </el-button>
              </div>
              <div v-else class="login-prompt">
                <router-link to="/login">登录</router-link> 后发表评论
              </div>
              
              <!-- 评论列表（支持楼中楼回复） -->
              <div class="comment-list">
                <div 
                  v-for="comment in comments" 
                  :key="comment.commentid" 
                  class="comment-item"
                >
                  <div class="comment-avatar">
                    <el-avatar :size="40" :src="comment.avatar">
                      {{ (comment.nickname || 'U').charAt(0) }}
                    </el-avatar>
                  </div>
                  <div class="comment-body">
                    <div class="comment-header">
                      <span class="comment-author">{{ comment.nickname || '匿名' }}</span>
                      <span class="comment-time">{{ formatDate(comment.createtime) }}</span>
                    </div>
                    <div class="comment-content">{{ comment.content }}</div>
                    <div class="comment-actions">
                      <span @click="agreeComment(comment)">
                        <el-icon><CaretTop /></el-icon> {{ comment.agreecount }}
                      </span>
                      <span @click="opposeComment(comment)">
                        <el-icon><CaretBottom /></el-icon> {{ comment.opposecount }}
                      </span>
                      <span v-if="userStore.isLoggedIn" @click="startReply(comment)">
                        <el-icon><ChatLineSquare /></el-icon> 回复
                      </span>
                    </div>

                    <!-- 回复输入框 -->
                    <div v-if="replyingTo === comment.commentid" class="reply-form">
                      <el-input
                        v-model="replyContent"
                        type="textarea"
                        :rows="2"
                        placeholder="回复..."
                      />
                      <div class="reply-form-actions">
                        <el-button size="small" @click="cancelReply">取消</el-button>
                        <el-button
                          size="small"
                          type="primary"
                          :loading="submittingReply"
                          :disabled="!replyContent.trim()"
                          @click="submitReply(comment)"
                        >
                          回复
                        </el-button>
                      </div>
                    </div>

                    <!-- 楼中楼回复列表 -->
                    <div v-if="comment.replies && comment.replies.length" class="reply-list">
                      <div
                        v-for="reply in comment.replies"
                        :key="reply.commentid"
                        class="reply-item"
                      >
                        <el-avatar :size="28" :src="reply.avatar">
                          {{ (reply.nickname || 'U').charAt(0) }}
                        </el-avatar>
                        <div class="reply-body">
                          <div class="comment-header">
                            <span class="comment-author">{{ reply.nickname || '匿名' }}</span>
                            <span class="comment-time">{{ formatDate(reply.createtime) }}</span>
                          </div>
                          <div class="comment-content">{{ reply.content }}</div>
                          <div class="comment-actions">
                            <span @click="agreeComment(reply)">
                              <el-icon><CaretTop /></el-icon> {{ reply.agreecount }}
                            </span>
                            <span @click="opposeComment(reply)">
                              <el-icon><CaretBottom /></el-icon> {{ reply.opposecount }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <EmptyState v-if="comments.length === 0" description="暂无评论" compact />
              </div>
            </section>
          </template>
          
          <el-empty v-else-if="!loading" description="文章不存在" />
        </div>
      </el-col>
        <el-col :span="7" :xs="24">
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
 * 包含 PDF 预览和 MathJax 公式渲染功能。
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ElementPlus from 'element-plus'
import { View, Star, Edit, CaretTop, CaretBottom, ChatLineSquare } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import { articleApi, commentApi, favoriteApi } from '@/api'
import Sidebar from '@/components/sidebar/Sidebar.vue'
import PdfViewer from '@/components/viewer/PdfViewer.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { createApp } from 'vue'

// 存储创建的PDF查看器应用实例，用于清理
const pdfViewerApps = []

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

// 状态
const article = ref(null)
const comments = ref([])
const loading = ref(true)
const isFavorited = ref(false)
const favoriteLoading = ref(false)
const newComment = ref('')
const submittingComment = ref(false)
const articleBodyRef = ref(null)

// 回复（楼中楼）状态
const replyingTo = ref(null)
const replyContent = ref('')
const submittingReply = ref(false)

/**
 * 评论总数（含楼中楼回复）
 */
const totalComments = computed(() => {
  return comments.value.reduce((sum, c) => sum + 1 + (c.replies ? c.replies.length : 0), 0)
})

/**
 * 文章分类名称
 */
const typeName = computed(() => {
  if (!article.value) return ''
  return articleStore.getTypeName(article.value.type)
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
 * 渲染数学公式
 * 支持 MathJax 2.x and 3.x
 */
function renderMathFormulas() {
  if (!articleBodyRef.value) return
  
  // 延迟执行确保DOM完全更新
  setTimeout(() => {
    if (window.MathJax) {
      try {
        // MathJax 3.x
        if (window.MathJax.typeset) {
          window.MathJax.typeset([articleBodyRef.value])
          console.log('MathJax公式渲染成功')
        } 
        // MathJax 2.x
        else if (window.MathJax.Hub) {
          window.MathJax.Hub.Queue(['Typeset', window.MathJax.Hub, articleBodyRef.value])
        }
      } catch (e) {
        console.error('MathJax渲染失败:', e)
      }
    }
  }, 100)
}

/**
 * 替换文章内容中的PDF占位符为PDF查看器组件
 * 动态挂载 Vue 组件到 DOM 节点
 */
function replacePdfPlaceholders() {
  if (!articleBodyRef.value) return
  
  // 清理之前创建的应用实例
  pdfViewerApps.forEach(app => {
    try { app.unmount() } catch (e) { /* already unmounted, ignore */ }
  })
  pdfViewerApps.length = 0
  
  // 查找所有PDF占位符
  const placeholders = articleBodyRef.value.querySelectorAll('.pdf-viewer-placeholder')
  console.log('Found PDF placeholders:', placeholders.length)
  
  placeholders.forEach((placeholder) => {
    const pdfUrl = placeholder.getAttribute('data-pdf-url')
    console.log('PDF URL:', pdfUrl)
    if (!pdfUrl) return
    
    // 创建容器div
    const container = document.createElement('div')
    container.className = 'pdf-viewer-wrapper'
    container.style.margin = '20px 0'
    
    // 创建Vue应用实例并挂载PDF查看器组件，注入ElementPlus
    const app = createApp(PdfViewer, { pdfUrl })
    app.use(ElementPlus)
    app.mount(container)
    pdfViewerApps.push(app)
    
    // 替换占位符
    if (placeholder.parentNode) {
      placeholder.parentNode.replaceChild(container, placeholder)
    }
  })
  
  // 同时检查是否有PDF链接需要转换为查看器
  const pdfLinks = articleBodyRef.value.querySelectorAll('a[href$=".pdf"]')
  pdfLinks.forEach((link) => {
    const href = link.getAttribute('href')
    if (href && href.includes('/api/uploads/')) {
      // 检查是否已经有占位符，避免重复
      const existing = link.closest('.pdf-viewer-wrapper')
      if (!existing) {
        const container = document.createElement('div')
        container.className = 'pdf-viewer-wrapper'
        container.style.margin = '20px 0'
        
        const app = createApp(PdfViewer, { pdfUrl: href })
        app.use(ElementPlus)
        app.mount(container)
        pdfViewerApps.push(app)
        
        if (link.parentNode) {
          link.parentNode.replaceChild(container, link)
        }
      }
    }
  })
}

/**
 * 获取评论列表
 */
async function fetchComments() {
  try {
    const res = await commentApi.getByArticle(route.params.id, { page: 1, page_size: 50 })
    comments.value = res.data
  } catch (error) {
    console.error('获取评论失败:', error)
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
 * 提交评论
 */
async function submitComment() {
  if (!newComment.value.trim()) return
  
  submittingComment.value = true
  try {
    await commentApi.create({
      articleid: article.value.articleid,
      content: newComment.value.trim()
    })
    newComment.value = ''
    await fetchComments()
    ElMessage.success('评论发表成功')
  } catch (error) {
    console.error('发表评论失败:', error)
  } finally {
    submittingComment.value = false
  }
}

/**
 * 开始回复某条评论（楼中楼）
 * @param {Object} comment - 被回复的评论
 */
function startReply(comment) {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login' })
    return
  }
  replyingTo.value = comment.commentid
  replyContent.value = ''
}

/**
 * 取消回复
 */
function cancelReply() {
  replyingTo.value = null
  replyContent.value = ''
}

/**
 * 提交回复
 * @param {Object} comment - 被回复的顶层评论
 */
async function submitReply(comment) {
  if (!replyContent.value.trim()) return

  submittingReply.value = true
  try {
    await commentApi.create({
      articleid: article.value.articleid,
      content: replyContent.value.trim(),
      replyid: comment.commentid
    })
    cancelReply()
    await fetchComments()
    ElMessage.success('回复成功')
  } catch (error) {
    console.error('回复失败:', error)
  } finally {
    submittingReply.value = false
  }
}

/**
 * 点赞评论。后端 vote 接口仅返回成功，前端本地自增计数。
 * @param {Object} comment - 评论对象
 */
async function agreeComment(comment) {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login' })
    return
  }
  
  try {
    await commentApi.agree(comment.commentid)
    comment.agreecount = (comment.agreecount || 0) + 1
  } catch (error) {
    console.error('点赞失败:', error)
  }
}

/**
 * 反对评论。后端 vote 接口仅返回成功，前端本地自增计数。
 * @param {Object} comment - 评论对象
 */
async function opposeComment(comment) {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login' })
    return
  }
  
  try {
    await commentApi.oppose(comment.commentid)
    comment.opposecount = (comment.opposecount || 0) + 1
  } catch (error) {
    console.error('踩失败:', error)
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
  pdfViewerApps.forEach(app => {
    try { app.unmount() } catch (e) { /* already unmounted, ignore */ }
  })
  pdfViewerApps.length = 0
  
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

.article-container {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  padding: 30px;
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

/* 评论区 */
.comment-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid var(--wn-color-border);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--wn-color-text);
}

.comment-form {
  margin-bottom: 30px;
}

.comment-form .el-button {
  margin-top: 10px;
}

.login-prompt {
  padding: 15px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-sm);
  text-align: center;
  margin-bottom: 30px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comment-item {
  display: flex;
  gap: 15px;
}

.comment-body {
  flex: 1;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.comment-author {
  font-weight: 500;
  color: var(--wn-color-text);
}

.comment-time {
  font-size: 12px;
  color: var(--wn-color-text-muted);
}

.comment-content {
  color: var(--wn-color-text-secondary);
  line-height: 1.6;
}

.comment-actions {
  margin-top: 10px;
  display: flex;
  gap: 20px;
}

/* PDF查看器样式 */
.pdf-viewer-wrapper {
  margin: 20px 0;
  width: 100%;
}

.comment-actions span {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--wn-color-text-muted);
  font-size: 13px;
  transition: color 0.3s;
}

.comment-actions span:hover {
  color: var(--wn-color-primary);
}

/* 楼中楼回复 */
.reply-form {
  margin-top: 12px;
}

.reply-form-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.reply-list {
  margin-top: 12px;
  padding-left: 12px;
  border-left: 2px solid var(--wn-color-border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reply-item {
  display: flex;
  gap: 10px;
}

.reply-body {
  flex: 1;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .comment-item {
    gap: 10px;
  }
  .reply-list {
    padding-left: 8px;
  }
  .comment-actions {
    flex-wrap: wrap;
  }
}
</style>
