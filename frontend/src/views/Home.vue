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
  padding: var(--wn-space-5) 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.home-container {
  width: 100%;
  max-width: 1200px;          /* 最大阅读宽度阈值 */
  margin: 0 auto;             /* 水平居中（仅宽屏视觉上生效）*/
  padding: 0 var(--wn-space-5);
}

@media (max-width: 768px) {
  .home-container {
    padding: 0 var(--wn-space-4);  /* 移动端两侧留边 */
  }
}

.main-content {
  padding: var(--wn-space-5);
}
</style>
