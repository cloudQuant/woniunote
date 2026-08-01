<template>
  <div class="category-page">
    <div class="category-container">
      <el-row :gutter="24" class="category-layout">
        <el-col :span="17" :xs="24" class="category-main-column">
          <div class="main-content">
            <h2 class="section-title">{{ categoryName }}</h2>
            
            <!-- 子分类标签 -->
            <div class="sub-categories" v-if="subCategories.length > 0">
              <el-tag 
                v-for="sub in subCategories" 
                :key="sub.id"
                :type="currentType == sub.id ? '' : 'info'"
                @click="selectSubCategory(sub.id)"
                class="category-tag"
              >
                {{ sub.name }}
              </el-tag>
            </div>
            
            <ArticleList 
              :type="currentType" 
              :page="currentPage"
              @loaded="onArticlesLoaded"
              @page-change="handlePageChange"
            />
          </div>
        </el-col>
        <el-col :span="7" :xs="24" class="category-sidebar-column">
          <Sidebar />
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @component Category
 * @description 文章分类页面组件
 * 展示指定分类下的文章列表。
 * 支持主分类和子分类的筛选，点击子分类可快速切换。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useArticleStore } from '@/stores/article'
import ArticleList from '@/components/article/ArticleList.vue'
import Sidebar from '@/components/sidebar/Sidebar.vue'

const route = useRoute()
const router = useRouter()
const articleStore = useArticleStore()

const currentType = ref(null)
const articlesTotal = ref(0)

// 从路由获取当前页码
const currentPage = computed(() => {
  return parseInt(route.params.page) || 1
})

const categoryName = computed(() => {
  return articleStore.getTypeName(route.params.type) || '分类'
})

const subCategories = computed(() => {
  const mainType = parseInt(route.params.type)
  if (mainType >= 100) return []
  
  const subs = []
  const types = articleStore.articleTypes
  
  for (const [id, name] of Object.entries(types)) {
    const typeId = parseInt(id)
    if (typeId >= mainType * 100 && typeId < (mainType + 1) * 100) {
      subs.push({ id: typeId, name })
    }
  }
  
  return subs
})

function selectSubCategory(typeId) {
  // 切换子分类时重置到第1页
  router.push({ name: 'Category', params: { type: typeId, page: 1 } })
}

function handlePageChange(page) {
  router.push({ name: 'Category', params: { type: currentType.value, page } })
}

function onArticlesLoaded({ total }) {
  articlesTotal.value = total
}

watch(() => route.params.type, (newType) => {
  currentType.value = parseInt(newType)
}, { immediate: true })

onMounted(async () => {
  await articleStore.fetchArticleTypes()
})
</script>

<style scoped>
.category-page {
  padding: var(--wn-space-5) 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.category-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--wn-space-5);
}

.category-layout {
  align-items: flex-start;
}

.category-main-column {
  min-width: 0;
}

/* 桌面端把检索与热门文章置于左侧；DOM 顺序仍保留文章优先。 */
.category-sidebar-column {
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

.sub-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
  padding: 15px;
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-sm);
}

.category-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.category-tag:hover {
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .category-page {
    padding: var(--wn-space-4) 0;
  }

  .category-container {
    padding: 0 var(--wn-space-4);
  }

  /* 小屏恢复内容优先，避免搜索与热门文章挤占首屏阅读空间。 */
  .category-sidebar-column {
    order: initial;
    margin-top: var(--wn-space-4);
  }
}
</style>
