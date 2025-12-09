<template>
  <div class="search-page">
    <div class="container">
      <el-row :gutter="20">
        <el-col :span="17" :xs="24">
          <div class="main-content">
            <h2 class="section-title">
              搜索结果：{{ keyword }}
              <span class="result-count" v-if="total > 0">共 {{ total }} 篇</span>
            </h2>
            
            <ArticleList :keyword="keyword" @loaded="onLoaded" />
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
 * @component Search
 * @description 搜索结果页面组件
 * 展示根据关键字搜索到的文章列表。
 */
import { ref, computed, watch } from 'vue'
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
  background: #f5f7fa;
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px;
  padding: 15px;
  background: #fff;
  border-left: 4px solid #409eff;
  border-radius: 4px;
  color: #303133;
}

.result-count {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
  margin-left: 10px;
}
</style>
