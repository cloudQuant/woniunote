<template>
  <aside class="sidebar">
    <!-- 搜索框 -->
    <div class="sidebar-card search-card">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入关键字"
        @keyup.enter="handleSearch"
        clearable
      >
        <template #append>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </template>
      </el-input>
    </div>
    
    <!-- 热门文章 -->
    <div class="sidebar-card">
      <h3 class="sidebar-title">热门文章</h3>
      <ul class="article-list">
        <li v-for="(article, index) in hotArticles.most" :key="article.articleid">
          <router-link :to="{ name: 'ArticleDetail', params: { id: article.articleid } }">
            <span class="list-num">{{ index + 1 }}.</span>{{ article.headline }}
          </router-link>
        </li>
        <li v-if="!hotArticles.most || hotArticles.most.length === 0" class="empty-tip">
          暂无文章
        </li>
      </ul>
    </div>
    
    <!-- 推荐文章 -->
    <div class="sidebar-card" v-if="hotArticles.recommended && hotArticles.recommended.length > 0">
      <h3 class="sidebar-title">推荐文章</h3>
      <ul class="article-list">
        <li v-for="(article, index) in hotArticles.recommended" :key="article.articleid">
          <router-link :to="{ name: 'ArticleDetail', params: { id: article.articleid } }">
            <span class="list-num">{{ index + 1 }}.</span>{{ article.headline }}
          </router-link>
        </li>
      </ul>
    </div>
    
    <!-- 回到顶部 -->
    <div class="back-to-top" v-show="showBackToTop" @click="scrollToTop">
      <el-icon><ArrowUp /></el-icon>
      <span>回到顶部</span>
    </div>
  </aside>
</template>

<script setup>
/**
 * @component Sidebar
 * @description 侧边栏组件
 * 包含搜索框、热门文章列表、推荐文章列表和回到顶部按钮。
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowUp } from '@element-plus/icons-vue'
import { useArticleStore } from '@/stores/article'

const router = useRouter()
const articleStore = useArticleStore()

// 状态
const searchKeyword = ref('')
const showBackToTop = ref(false)

// 计算属性
const hotArticles = computed(() => articleStore.hotArticles)

/**
 * 处理搜索
 * 跳转到搜索结果页
 */
function handleSearch() {
  if (searchKeyword.value.trim()) {
    router.push({ name: 'Search', query: { keyword: searchKeyword.value } })
  }
}

/**
 * 滚动到顶部
 */
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

/**
 * 监听滚动事件
 * 控制回到顶部按钮的显示/隐藏
 */
function handleScroll() {
  showBackToTop.value = window.scrollY > 300
}

// 生命周期钩子
onMounted(async () => {
  await articleStore.fetchHotArticles()
  await articleStore.fetchArticleTypes()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 120px;
}

.sidebar-card {
  background: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  margin-bottom: 15px;
  overflow: hidden;
}

.search-card {
  padding: 15px;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  padding: 12px 15px;
  background: #17a2b8;
  color: #fff;
  text-align: center;
}

.article-list {
  list-style: none;
  padding: 10px 15px;
  margin: 0;
}

.article-list li {
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
}

.article-list li:last-child {
  border-bottom: none;
}

.article-list a {
  color: #606266;
  font-size: 14px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.3s;
  line-height: 1.5;
}

.article-list a:hover {
  color: #409eff;
}

.list-num {
  color: #409eff;
  margin-right: 5px;
}

.empty-tip {
  color: #909399;
  font-size: 14px;
  text-align: center;
}

.back-to-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 12px;
  background: #17a2b8;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.back-to-top:hover {
  background: #138496;
  transform: translateY(-2px);
}
</style>
