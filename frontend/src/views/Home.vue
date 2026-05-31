<template>
  <div class="home-page">
    <div class="home-container">
      <el-row :gutter="24">
        <el-col :span="17" :xs="24">
          <div class="main-content">
            <ArticleList :page="currentPage" @page-change="handlePageChange" />
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
 * @component Home
 * @description 首页组件
 * 展示文章列表和侧边栏。支持分页浏览。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ArticleList from '@/components/article/ArticleList.vue'
import Sidebar from '@/components/sidebar/Sidebar.vue'

const route = useRoute()
const router = useRouter()

/**
 * 当前页码
 * 从路由参数 page 获取，默认为 1
 */
const currentPage = computed(() => {
  return parseInt(route.params.page) || 1
})

/**
 * 处理分页变化
 * 跳转到对应的分页路由
 * @param {number} page - 目标页码
 */
function handlePageChange(page) {
  if (page === 1) {
    router.push({ name: 'Home' })
  } else {
    router.push({ name: 'HomePage', params: { page } })
  }
}
</script>

<style scoped>
.home-page {
  padding: 20px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.home-container {
  /* 首页全宽容器，让文章和侧边栏尽量贴近屏幕两侧 */
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 0;
}

.main-content {
  padding: 20px;
}

.sidebar-wrapper {
  width: 280px;
  padding: 20px;
}

@media (max-width: 992px) {
  .sidebar-wrapper {
    width: 100%;
  }
}
</style>
