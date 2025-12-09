<template>
  <div class="my-favorites-page">
    <h3 class="page-title">我的收藏</h3>
    
    <div class="favorites-list" v-loading="loading">
      <div 
        v-for="item in favorites" 
        :key="item.favoriteid" 
        class="favorite-item"
      >
        <div class="article-info">
          <router-link 
            :to="{ name: 'ArticleDetail', params: { id: item.article?.articleid } }"
            class="article-title"
          >
            {{ item.article?.headline }}
          </router-link>
          <div class="article-meta">
            <span>{{ formatDate(item.createtime) }} 收藏</span>
            <span>阅读 {{ item.article?.readcount }}</span>
          </div>
        </div>
        <el-popconfirm 
          title="确定要取消收藏吗？" 
          @confirm="removeFavorite(item)"
        >
          <template #reference>
            <el-button type="warning" size="small" text>取消收藏</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>
    
    <div class="pagination-container" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchFavorites"
      />
    </div>
    
    <el-empty v-if="!loading && favorites.length === 0" description="暂无收藏" />
  </div>
</template>

<script setup>
/**
 * @component MyFavorites
 * @description 我的收藏列表组件
 * 展示用户收藏的文章，提供跳转到文章详情和取消收藏的功能。
 * 显示文章标题、收藏时间和文章的阅读量。
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { favoriteApi } from '@/api'

const favorites = ref([])
const loading = ref(true)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function fetchFavorites() {
  loading.value = true
  try {
    const res = await favoriteApi.getList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    favorites.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取收藏列表失败:', error)
  } finally {
    loading.value = false
  }
}

async function removeFavorite(item) {
  try {
    await favoriteApi.remove(item.articleid)
    ElMessage.success('已取消收藏')
    await fetchFavorites()
  } catch (error) {
    console.error('取消收藏失败:', error)
  }
}

onMounted(() => {
  fetchFavorites()
})
</script>

<style scoped>
.my-favorites-page {
  padding: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: #303133;
}

.favorites-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.favorite-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: background 0.3s;
}

.favorite-item:hover {
  background: #ebeef5;
}

.article-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  display: block;
  margin-bottom: 8px;
}

.article-title:hover {
  color: #409eff;
}

.article-meta {
  font-size: 13px;
  color: #909399;
  display: flex;
  gap: 15px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
