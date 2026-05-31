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
    <div
      class="back-to-top"
      v-show="showBackToTop"
      role="button"
      tabindex="0"
      @click="scrollToTop"
      @keydown.enter.prevent="scrollToTop"
      @keydown.space.prevent="scrollToTop"
    >
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
  top: 80px;
  width: 100%;
}

.sidebar-card {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-sm);
  border: 1px solid var(--wn-color-border);
  margin-bottom: var(--wn-space-4);
  overflow: hidden;
}

.search-card {
  padding: var(--wn-space-4);
}

.sidebar-title {
  font-size: var(--wn-font-size-md);
  font-weight: 600;
  margin: 0;
  padding: var(--wn-space-3) var(--wn-space-4);
  background: var(--wn-color-primary);
  color: var(--wn-color-on-primary);
  text-align: center;
}

.article-list {
  list-style: none;
  padding: var(--wn-space-3) var(--wn-space-4);
  margin: 0;
}

.article-list li {
  padding: var(--wn-space-2) 0;
  border-bottom: 1px dashed var(--wn-color-border);
}

.article-list li:last-child {
  border-bottom: none;
}

.article-list a {
  color: var(--wn-color-text-secondary);
  font-size: var(--wn-font-size-base);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--wn-transition-base);
  line-height: var(--wn-line-height-snug);
}

.article-list a:hover {
  color: var(--wn-color-primary);
}

.list-num {
  color: var(--wn-color-primary);
  margin-right: var(--wn-space-1);
}

.empty-tip {
  color: var(--wn-color-text-muted);
  font-size: var(--wn-font-size-base);
  text-align: center;
}

.back-to-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--wn-space-1);
  padding: var(--wn-space-3);
  background: var(--wn-color-primary);
  color: var(--wn-color-on-primary);
  border-radius: var(--wn-radius-sm);
  cursor: pointer;
  transition: background var(--wn-transition-base), transform var(--wn-transition-base);
  font-size: var(--wn-font-size-base);
}

.back-to-top:hover {
  background: var(--wn-color-primary-active);
  transform: translateY(var(--wn-hover-lift));
}

@media (prefers-reduced-motion: reduce) {
  .back-to-top:hover {
    transform: none;
  }
}
</style>
