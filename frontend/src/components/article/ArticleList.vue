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
import { ref, watch, onMounted, computed } from 'vue'
import ArticleCard from './ArticleCard.vue'
import Pagination from '@/components/common/Pagination.vue'
import { articleApi } from '@/api'

const props = defineProps({
  type: {
    type: [Number, String],
    default: null
  },
  keyword: {
    type: String,
    default: ''
  },
  page: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['loaded', 'page-change'])

const articles = ref([])
const loading = ref(true)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(0)

// 使用计算属性同步页码
const currentPage = computed({
  get: () => props.page,
  set: (val) => emit('page-change', val)
})

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

function handlePageChange(page) {
  emit('page-change', page)
}

// 监听所有相关属性变化
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
