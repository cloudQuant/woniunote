<template>
  <div class="article-detail-page">
    <div class="container">
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
              <h3 class="section-title">评论 ({{ comments.length }})</h3>
              
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
              
              <!-- 评论列表 -->
              <div class="comment-list">
                <div 
                  v-for="comment in comments" 
                  :key="comment.commentid" 
                  class="comment-item"
                >
                  <div class="comment-avatar">
                    <el-avatar :size="40" :src="comment.user?.avatar">
                      {{ comment.user?.nickname?.charAt(0) || 'U' }}
                    </el-avatar>
                  </div>
                  <div class="comment-body">
                    <div class="comment-header">
                      <span class="comment-author">{{ comment.user?.nickname || '匿名' }}</span>
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
                    </div>
                  </div>
                </div>
                
                <el-empty v-if="comments.length === 0" description="暂无评论" />
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
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ElementPlus from 'element-plus'
import { View, Star, Edit, CaretTop, CaretBottom } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/article'
import { articleApi, commentApi, favoriteApi } from '@/api'
import Sidebar from '@/components/sidebar/Sidebar.vue'
import PdfViewer from '@/components/viewer/PdfViewer.vue'
import { createApp } from 'vue'

// 存储创建的PDF查看器应用实例，用于清理
const pdfViewerApps = []

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()

const article = ref(null)
const comments = ref([])
const loading = ref(true)
const isFavorited = ref(false)
const favoriteLoading = ref(false)
const newComment = ref('')
const submittingComment = ref(false)
const articleBodyRef = ref(null)

const typeName = computed(() => {
  if (!article.value) return ''
  return articleStore.getTypeName(article.value.type)
})

const canEdit = computed(() => {
  if (!userStore.isLoggedIn || !article.value) return false
  return article.value.userid === userStore.user?.userid || userStore.isEditor
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

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

// 渲染数学公式
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

// 替换文章内容中的PDF占位符为PDF查看器组件
function replacePdfPlaceholders() {
  if (!articleBodyRef.value) return
  
  // 清理之前创建的应用实例
  pdfViewerApps.forEach(app => {
    try { app.unmount() } catch(e) {}
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

async function fetchComments() {
  try {
    const res = await commentApi.getByArticle(route.params.id, { page: 1, page_size: 50 })
    comments.value = res.data
  } catch (error) {
    console.error('获取评论失败:', error)
  }
}

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

async function agreeComment(comment) {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login' })
    return
  }
  
  try {
    const res = await commentApi.agree(comment.commentid)
    comment.agreecount = res.data.agreecount
  } catch (error) {
    console.error('点赞失败:', error)
  }
}

async function opposeComment(comment) {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'Login' })
    return
  }
  
  try {
    const res = await commentApi.oppose(comment.commentid)
    comment.opposecount = res.data.opposecount
  } catch (error) {
    console.error('踩失败:', error)
  }
}

function editArticle() {
  router.push({ name: 'EditArticle', params: { id: article.value.articleid } })
}

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
    try { app.unmount() } catch(e) {}
  })
  pdfViewerApps.length = 0
})
</script>

<style scoped>
.article-detail-page {
  padding: 20px 0;
  background: #f5f7fa;
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.article-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.article-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.article-title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 15px;
}

.article-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: #909399;
  font-size: 14px;
}

.author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.divider {
  color: #dcdfe6;
}

.views {
  display: flex;
  align-items: center;
  gap: 4px;
}

.article-body {
  font-size: 16px;
  line-height: 1.8;
  color: #606266;
}

.article-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.article-body :deep(pre) {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
}

.article-body :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: Consolas, Monaco, monospace;
}

/* 表格样式 */
.article-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.article-body :deep(th),
.article-body :deep(td) {
  border: 1px solid #e0e0e0;
  padding: 12px 16px;
  text-align: left;
  vertical-align: top;
}

.article-body :deep(th) {
  background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
  font-weight: 600;
  color: #333;
}

.article-body :deep(tr:nth-child(even)) {
  background-color: #f8f9fa;
}

.article-body :deep(tr:hover) {
  background-color: #e8f4fd;
}

.article-body :deep(td:first-child) {
  font-weight: 500;
}

.article-footer {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.article-actions {
  display: flex;
  gap: 15px;
}

/* 评论区 */
.comment-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid #ebeef5;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: #303133;
}

.comment-form {
  margin-bottom: 30px;
}

.comment-form .el-button {
  margin-top: 10px;
}

.login-prompt {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
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
  color: #303133;
}

.comment-time {
  font-size: 12px;
  color: #909399;
}

.comment-content {
  color: #606266;
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
  color: #909399;
  font-size: 13px;
  transition: color 0.3s;
}

.comment-actions span:hover {
  color: #409eff;
}
</style>
