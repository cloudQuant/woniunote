<template>
  <div class="my-drafts-page">
    <h3 class="page-title">我的草稿</h3>
    
    <div class="drafts-list" v-loading="loading">
      <div 
        v-for="item in drafts" 
        :key="item.articleid" 
        class="draft-item"
      >
        <div class="draft-info">
          <div class="draft-title">{{ item.headline }}</div>
          <div class="draft-meta">
            <span>最后编辑: {{ formatDate(item.updatetime) }}</span>
            <el-tag size="small" type="info">{{ getTypeName(item.type) }}</el-tag>
          </div>
        </div>
        <div class="draft-actions">
          <el-button 
            type="primary" 
            size="small"
            @click="editDraft(item)"
          >
            继续编辑
          </el-button>
          <el-popconfirm 
            title="确定要删除这篇草稿吗？" 
            @confirm="deleteDraft(item)"
          >
            <template #reference>
              <el-button type="danger" size="small" text>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>
    
    <div class="pagination-container" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchDrafts"
      />
    </div>
    
    <el-empty v-if="!loading && drafts.length === 0" description="暂无草稿">
      <el-button type="primary" @click="$router.push({ name: 'WriteArticle' })">
        写篇文章
      </el-button>
    </el-empty>
  </div>
</template>

<script setup>
/**
 * @component MyDrafts
 * @description 我的草稿箱组件
 * 展示用户保存的草稿文章，支持编辑（继续写作）和删除操作。
 * 显示草稿的标题、最后编辑时间和分类信息。
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { draftApi, articleApi } from '@/api'

const router = useRouter()
const drafts = ref([])
const loading = ref(true)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 文章类型映射
const typeNames = {
  1: '交易策略', 2: '量化框架', 3: '投资', 4: '理财',
  5: '区块链与defi', 6: '机器学习', 7: '编程', 8: '笔记', 9: '教程'
}

function getTypeName(type) {
  if (type >= 100) {
    const parentType = Math.floor(type / 100)
    return typeNames[parentType] || '未分类'
  }
  return typeNames[type] || '未分类'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function fetchDrafts() {
  loading.value = true
  try {
    const res = await draftApi.getMyDrafts({
      page: currentPage.value,
      page_size: pageSize.value
    })
    drafts.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取草稿列表失败:', error)
  } finally {
    loading.value = false
  }
}

function editDraft(item) {
  router.push({ name: 'EditArticle', params: { id: item.articleid } })
}

async function deleteDraft(item) {
  try {
    await articleApi.delete(item.articleid)
    ElMessage.success('草稿已删除')
    await fetchDrafts()
  } catch (error) {
    console.error('删除草稿失败:', error)
  }
}

onMounted(() => {
  fetchDrafts()
})
</script>

<style scoped>
.my-drafts-page {
  padding: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--wn-color-text);
}

.drafts-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.draft-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-md);
  transition: background 0.3s;
}

.draft-item:hover {
  background: var(--wn-color-surface-2);
}

.draft-info {
  flex: 1;
  min-width: 0;
}

.draft-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--wn-color-text);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.draft-meta {
  font-size: 13px;
  color: var(--wn-color-text-muted);
  display: flex;
  align-items: center;
  gap: 15px;
}

.draft-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
