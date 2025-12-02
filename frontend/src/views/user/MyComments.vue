<template>
  <div class="my-comments-page">
    <h3 class="page-title">我的评论</h3>
    
    <div class="comments-list" v-loading="loading">
      <div 
        v-for="item in comments" 
        :key="item.commentid" 
        class="comment-item"
      >
        <div class="comment-content">
          <div class="comment-text">{{ item.content }}</div>
          <div class="comment-meta">
            <router-link 
              v-if="item.article_id"
              :to="{ name: 'ArticleDetail', params: { id: item.article_id } }"
              class="article-link"
            >
              {{ item.article_headline || '查看文章' }}
            </router-link>
            <span class="comment-time">{{ formatDate(item.createtime) }}</span>
            <span class="comment-stats">
              <span>赞 {{ item.agreecount }}</span>
              <span>踩 {{ item.opposecount }}</span>
            </span>
          </div>
        </div>
        <el-popconfirm 
          title="确定要删除这条评论吗？" 
          @confirm="deleteComment(item)"
        >
          <template #reference>
            <el-button type="danger" size="small" text>删除</el-button>
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
        @current-change="fetchComments"
      />
    </div>
    
    <el-empty v-if="!loading && comments.length === 0" description="暂无评论" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { myCommentApi, commentApi } from '@/api'

const comments = ref([])
const loading = ref(true)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function fetchComments() {
  loading.value = true
  try {
    const res = await myCommentApi.getMyComments({
      page: currentPage.value,
      page_size: pageSize.value
    })
    comments.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取评论列表失败:', error)
  } finally {
    loading.value = false
  }
}

async function deleteComment(item) {
  try {
    await commentApi.delete(item.commentid)
    ElMessage.success('评论已删除')
    await fetchComments()
  } catch (error) {
    console.error('删除评论失败:', error)
  }
}

onMounted(() => {
  fetchComments()
})
</script>

<style scoped>
.my-comments-page {
  padding: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: #303133;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.comment-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: background 0.3s;
}

.comment-item:hover {
  background: #ebeef5;
}

.comment-content {
  flex: 1;
  min-width: 0;
}

.comment-text {
  font-size: 15px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 10px;
  word-break: break-word;
}

.comment-meta {
  font-size: 13px;
  color: #909399;
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: center;
}

.article-link {
  color: #409eff;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-link:hover {
  text-decoration: underline;
}

.comment-stats {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
