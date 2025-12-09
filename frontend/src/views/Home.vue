<template>
  <div class="home-page">
    <div class="container">
      <el-row :gutter="20">
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
  background: #f5f7fa;
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.main-content {
  min-height: 400px;
}

@media (max-width: 768px) {
  .el-col-xs-24 {
    margin-bottom: 20px;
  }
}
</style>
