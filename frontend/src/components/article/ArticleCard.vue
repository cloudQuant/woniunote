<template>
  <div class="article-item" @click="goToDetail">
    <!-- 左侧缩略图 -->
    <div class="article-thumbnail">
      <img 
        :src="thumbnailUrl" 
        :alt="article.headline"
        @error="handleImageError"
      />
    </div>
    
    <!-- 右侧内容 -->
    <div class="article-content">
      <h3 class="article-title">{{ article.headline }}</h3>
      
      <div class="article-meta">
        <span class="meta-item">作者: {{ article.author?.nickname || '匿名' }}</span>
        <span class="meta-item">类别: {{ typeName }}</span>
        <span class="meta-item">日期: {{ formatDate(article.createtime) }}</span>
        <span class="meta-item">阅读: {{ article.readcount || 0 }}次</span>
        <span class="meta-item">消耗积分: {{ article.credit || 0 }}分</span>
      </div>
      
      <p class="article-excerpt">{{ excerpt }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useArticleStore } from '@/stores/article'

const props = defineProps({
  article: {
    type: Object,
    required: true
  }
})

const router = useRouter()
const articleStore = useArticleStore()

// 生成缩略图：优先使用后端缩略图服务，其次使用本地SVG占位图
const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#6f7ad3']

// 缓存破坏版本号（更新缩略图后递增此值）
const THUMB_VERSION = 'v2'

const thumbnailUrl = computed(() => {
  // 1. 如果后端返回了具体的 thumbnail 字段，认为是 thumb 文件名，例如 "101.png"
  if (props.article.thumbnail) {
    // 如果已经是完整URL，直接返回
    if (props.article.thumbnail.startsWith('http://') || props.article.thumbnail.startsWith('https://')) {
      return props.article.thumbnail
    }
    // 否则走新后端缩略图路由（带版本号防止缓存）
    return `/api/thumb/${props.article.thumbnail}?${THUMB_VERSION}`
  }

  // 2. 如果没有 thumbnail，但有文章类型，则使用类型ID自动生成缩略图
  if (props.article.type) {
    return `/api/thumb/${props.article.type}.png?${THUMB_VERSION}`
  }

  // 3. 最后兜底：使用 SVG data URL 作为占位图
  const colorIndex = (props.article.articleid || 0) % colors.length
  const color = colors[colorIndex]
  const typeName = articleStore.getTypeName(props.article.type) || '文章'
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="130" viewBox="0 0 200 130">
    <rect fill="${color}" width="200" height="130"/>
    <text x="100" y="65" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="20" font-weight="bold" font-family="sans-serif">${typeName}</text>
  </svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
})

const typeName = computed(() => {
  return articleStore.getTypeName(props.article.type) || '未分类'
})

const excerpt = computed(() => {
  // 从content中提取纯文本摘要
  if (!props.article.content) return ''
  const text = props.article.content
    .replace(/<[^>]+>/g, '')  // 移除HTML标签
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text.length > 150 ? text.slice(0, 150) + '...' : text
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

function goToDetail() {
  router.push({ name: 'ArticleDetail', params: { id: props.article.articleid } })
}

// 图片加载失败时使用 SVG 占位图
function handleImageError(event) {
  const colorIndex = (props.article.articleid || 0) % colors.length
  const color = colors[colorIndex]
  const typeText = articleStore.getTypeName(props.article.type) || '文章'
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="130" viewBox="0 0 200 130">
    <rect fill="${color}" width="200" height="130"/>
    <text x="100" y="65" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="20" font-weight="bold" font-family="sans-serif">${typeText}</text>
  </svg>`
  event.target.src = `data:image/svg+xml,${encodeURIComponent(svg)}`
}
</script>

<style scoped>
/* 与原站 woniunote 一致的文章卡片样式 */
.article-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  background: #fff;
  border-radius: 5px;
  margin-bottom: 15px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s;
}

.article-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.article-thumbnail {
  flex-shrink: 0;
  width: 226px;
  height: 136px;
  overflow: hidden;
  border-radius: 4px;
}

.article-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.article-item:hover .article-thumbnail img {
  transform: scale(1.02);
}

.article-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.article-title {
  font-size: 16px;
  font-weight: normal;
  color: #333;
  margin: 0 0 10px;
  line-height: 1.8;
  cursor: pointer;
}

.article-title:hover {
  color: #007bff;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: 10px;
  font-size: 14px;
  color: #666;
}

.meta-item {
  display: inline-flex;
  align-items: center;
}

.meta-item::after {
  content: '\00a0\00a0\00a0';
}

.meta-item:last-child::after {
  content: '';
}

.article-excerpt {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

@media (max-width: 768px) {
  .article-item {
    flex-direction: column;
  }
  
  .article-thumbnail {
    width: 100%;
    height: 180px;
    display: none;
  }
  
  .article-meta {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .meta-item::after {
    content: '';
  }
}
</style>
