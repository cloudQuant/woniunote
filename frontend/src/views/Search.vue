<template>
  <div class="search-page">
    <div class="container">
      <el-row :gutter="20" class="search-layout">
        <el-col :span="17" :xs="24" class="search-main-column">
          <div class="main-content">
            <h2 class="section-title">
              搜索结果：{{ keyword }}
              <span class="result-count" v-if="total > 0">共 {{ total }} 篇</span>
            </h2>
            
            <ArticleList :keyword="keyword" @loaded="onLoaded" />
          </div>
        </el-col>
        <el-col :span="7" :xs="24" class="search-sidebar-column">
          <Sidebar />
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @component Search
 * @description 搜索结果页面组件
 * 展示根据关键字搜索到的文章列表。
 */
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import ArticleList from '@/components/article/ArticleList.vue'
import Sidebar from '@/components/sidebar/Sidebar.vue'

const route = useRoute()

const total = ref(0)

const keyword = computed(() => route.query.keyword || '')

function onLoaded({ total: count }) {
  total.value = count
}
</script>

<style scoped>
.search-page {
  padding: 20px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.search-layout {
  align-items: flex-start;
}

.search-main-column {
  min-width: 0;
}

/* 桌面端把搜索与热门文章放到搜索结果左侧。 */
.search-sidebar-column {
  order: -1;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px;
  padding: 15px;
  background: var(--wn-color-surface);
  border-left: 4px solid var(--wn-color-primary);
  border-radius: var(--wn-radius-sm);
  color: var(--wn-color-text);
}

.result-count {
  font-size: 14px;
  font-weight: normal;
  color: var(--wn-color-text-muted);
  margin-left: 10px;
}

/* Element Plus 的 xs 栅格在 767px 以下切换为单列。 */
@media (max-width: 767px) {
  .container {
    padding: 0 var(--wn-space-4);
  }

  /* 小屏保留搜索结果优先的阅读顺序。 */
  .search-sidebar-column {
    order: initial;
    margin-top: var(--wn-space-4);
  }
}
</style>
