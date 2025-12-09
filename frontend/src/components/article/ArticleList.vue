<template>
  <div class="article-list">
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>
    
    <template v-else-if="articles.length > 0">
      <div class="article-grid">
        <ArticleCard 
          v-for="article in articles" 
          :key="article.articleid" 
          :article="article" 
        />
      </div>
      
      <Pagination 
        v-if="totalPages > 1"
        :current-page="currentPage"
        :total-pages="totalPages"
        @change="handlePageChange"
      />
    </template>
    
    <el-empty v-else description="暂无文章" />
  </div>
</template>

<script setup>
/**
 * @component ArticleList
 * @description 文章列表组件
 * 负责获取和展示文章列表，支持分页、分类筛选和关键字搜索。
 */
import { ref, watch, onMounted, computed } from 'vue'
import ArticleCard from './ArticleCard.vue'
import Pagination from '@/components/common/Pagination.vue'
import { articleApi } from '@/api'

const props = defineProps({
  /**
   * 文章分类 ID
   */
  type: {
    type: [Number, String],
    default: null
  },
  /**
   * 搜索关键字
   */
  keyword: {
    type: String,
    default: ''
  },
  /**
   * 当前页码
   */
  page: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits([
  /**
   * 列表加载完成事件
   * @arg {Object} data - 包含总条数等信息
   */
  'loaded', 
  /**
   * 页码改变事件
   * @arg {number} page - 新的页码
   */
  'page-change'
])

// 状态
const articles = ref([])
const loading = ref(true)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(0)

/**
 * 当前页码计算属性
 * 同步 props 和 emit
 */
const currentPage = computed({
  get: () => props.page,
  set: (val) => emit('page-change', val)
})

/**
 * 获取文章列表数据
 * 根据 props 中的筛选条件请求 API
 */
async function fetchArticles() {
  loading.value = true
  try {
    const params = {
      page: props.page,
      page_size: pageSize.value
    }
    
    if (props.type) {
      params.type = props.type
    }
    
    if (props.keyword) {
      params.keyword = props.keyword
    }
    
    const res = await articleApi.getList(params)
    articles.value = res.data
    total.value = res.total
    totalPages.value = res.total_pages
    
    emit('loaded', { total: res.total })
  } catch (error) {
    console.error('获取文章列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 处理页码变更
 * @param {number} page - 新页码
 */
function handlePageChange(page) {
  emit('page-change', page)
}

// 监听筛选条件变化，重新获取数据
watch([() => props.type, () => props.keyword, () => props.page], () => {
  fetchArticles()
}, { immediate: false })

onMounted(() => {
  fetchArticles()
})
</script>

<style scoped>
.article-list {
  padding: 0;
}

.loading-container {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.article-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
}
</style>
