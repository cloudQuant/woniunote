<template>
  <div class="cards-page">
    <div class="container">
      <div class="page-header">
        <h1>任务卡片</h1>
        <div class="header-actions">
          <el-button @click="showAddCategory = true">
            <el-icon><FolderAdd /></el-icon> 新建分类
          </el-button>
          <el-button type="primary" @click="showAddCard = true">
            <el-icon><Plus /></el-icon> 新建卡片
          </el-button>
        </div>
      </div>
      
      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon bg-blue"><el-icon><Tickets /></el-icon></div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.total }}</span>
            <span class="stat-label">总卡片</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon bg-orange"><el-icon><Timer /></el-icon></div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.in_progress }}</span>
            <span class="stat-label">进行中</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon bg-green"><el-icon><CircleCheck /></el-icon></div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.done }}</span>
            <span class="stat-label">已完成</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon bg-purple"><el-icon><Clock /></el-icon></div>
          <div class="stat-info">
            <span class="stat-value">{{ formatTime(stats.total_time) }}</span>
            <span class="stat-label">总用时</span>
          </div>
        </div>
      </div>
      
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filterCategory" placeholder="全部分类" clearable @change="fetchCards">
          <el-option 
            v-for="cat in categories" 
            :key="cat.id" 
            :label="cat.name" 
            :value="cat.id" 
          />
        </el-select>
        <el-select v-model="filterType" placeholder="全部优先级" clearable @change="fetchCards">
          <el-option :value="1" label="重要紧急" />
          <el-option :value="2" label="重要不紧急" />
          <el-option :value="3" label="紧急不重要" />
          <el-option :value="4" label="不重要不紧急" />
        </el-select>
        <el-radio-group v-model="filterDone" @change="fetchCards">
          <el-radio-button :value="null">全部</el-radio-button>
          <el-radio-button :value="0">进行中</el-radio-button>
          <el-radio-button :value="1">已完成</el-radio-button>
        </el-radio-group>
      </div>
      
      <!-- 卡片列表 -->
      <div class="cards-grid" v-loading="loading">
        <div 
          v-for="card in cards" 
          :key="card.id" 
          class="task-card"
          :class="{ 
            done: card.donetime,
            'in-progress': card.begintime && !card.donetime
          }"
        >
          <div class="card-header">
            <el-tag :type="getPriorityType(card.type)" size="small">
              {{ getPriorityName(card.type) }}
            </el-tag>
            <el-dropdown @command="handleCardAction($event, card)">
              <el-icon class="more-icon"><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          
          <h3 class="card-title">{{ card.headline }}</h3>
          <p class="card-content" v-if="card.content">{{ card.content }}</p>
          
          <div class="card-meta">
            <span v-if="card.usedtime > 0" class="time-badge">
              <el-icon><Clock /></el-icon> {{ formatTime(card.usedtime) }}
            </span>
            <span class="date-badge">{{ formatDate(card.createtime) }}</span>
          </div>
          
          <div class="card-actions">
            <template v-if="!card.donetime">
              <el-button 
                v-if="!card.begintime" 
                type="primary" 
                size="small"
                @click="startCard(card)"
              >
                <el-icon><VideoPlay /></el-icon> 开始
              </el-button>
              <template v-else>
                <el-button size="small" @click="stopCard(card)">
                  <el-icon><VideoPause /></el-icon> 暂停
                </el-button>
                <el-button type="success" size="small" @click="completeCard(card)">
                  <el-icon><Check /></el-icon> 完成
                </el-button>
              </template>
            </template>
            <el-button 
              v-else 
              size="small" 
              @click="reopenCard(card)"
            >
              <el-icon><RefreshLeft /></el-icon> 重新打开
            </el-button>
          </div>
        </div>
        
        <el-empty v-if="!loading && cards.length === 0" description="暂无卡片" />
      </div>
      
      <!-- 分页 -->
      <div class="pagination" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchCards"
        />
      </div>
    </div>
    
    <!-- 新建分类对话框 -->
    <el-dialog v-model="showAddCategory" title="新建分类" width="400px">
      <el-form>
        <el-form-item label="分类名称">
          <el-input v-model="newCategoryName" placeholder="请输入分类名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddCategory = false">取消</el-button>
        <el-button type="primary" @click="addCategory">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 新建/编辑卡片对话框 -->
    <el-dialog 
      v-model="showAddCard" 
      :title="editingCard ? '编辑卡片' : '新建卡片'" 
      width="500px"
    >
      <el-form :model="cardForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="cardForm.headline" placeholder="卡片标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="cardForm.content" type="textarea" :rows="3" placeholder="详细描述（选填）" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="cardForm.category_id" placeholder="选择分类" style="width: 100%">
            <el-option 
              v-for="cat in categories" 
              :key="cat.id" 
              :label="cat.name" 
              :value="cat.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="cardForm.type" style="width: 100%">
            <el-option :value="1" label="重要紧急" />
            <el-option :value="2" label="重要不紧急" />
            <el-option :value="3" label="紧急不重要" />
            <el-option :value="4" label="不重要不紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="重复任务">
          <el-switch v-model="cardForm.is_repeat" :active-value="1" :inactive-value="0" />
          <span class="form-tip">开启后完成任务时会自动创建新的副本</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeCardDialog">取消</el-button>
        <el-button type="primary" @click="saveCard">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @component Cards
 * @description 任务卡片管理页面组件
 * 提供看板式的任务管理功能，支持按分类、优先级筛选。
 * 包含任务计时、重复任务设置和统计看板功能。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Plus, FolderAdd, MoreFilled, Tickets, Timer, CircleCheck, Clock,
  VideoPlay, VideoPause, Check, RefreshLeft
} from '@element-plus/icons-vue'
import { cardApi } from '@/api'

// 数据
const categories = ref([])
const cards = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const filterCategory = ref(null)
const filterType = ref(null)
const filterDone = ref(null)

// 统计
const stats = reactive({
  total: 0,
  done: 0,
  pending: 0,
  in_progress: 0,
  total_time: 0
})

// 分类
const showAddCategory = ref(false)
const newCategoryName = ref('')

// 卡片表单
const showAddCard = ref(false)
const editingCard = ref(null)
const cardForm = reactive({
  headline: '',
  content: '',
  category_id: null,
  type: 2,
  is_repeat: 0
})

const PRIORITY_NAMES = {
  1: '重要紧急',
  2: '重要不紧急',
  3: '紧急不重要',
  4: '不重要不紧急'
}

function getPriorityName(type) {
  return PRIORITY_NAMES[type] || '未分类'
}

function getPriorityType(type) {
  const types = { 1: 'danger', 2: 'warning', 3: 'info', 4: '' }
  return types[type] || ''
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function formatTime(seconds) {
  if (!seconds) return '0分'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}时${minutes}分`
  }
  return `${minutes}分`
}

async function fetchCategories() {
  try {
    const res = await cardApi.getCategories()
    categories.value = res.data
    if (categories.value.length > 0 && !cardForm.category_id) {
      cardForm.category_id = categories.value[0].id
    }
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

async function fetchCards() {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (filterCategory.value) params.category_id = filterCategory.value
    if (filterType.value) params.type = filterType.value
    if (filterDone.value !== null) params.done = filterDone.value
    
    const res = await cardApi.getCards(params)
    cards.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取卡片失败:', error)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await cardApi.getStats()
    Object.assign(stats, res.data)
  } catch (error) {
    console.error('获取统计失败:', error)
  }
}

async function addCategory() {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  try {
    await cardApi.createCategory({ name: newCategoryName.value })
    ElMessage.success('创建成功')
    showAddCategory.value = false
    newCategoryName.value = ''
    await fetchCategories()
  } catch (error) {
    console.error('创建分类失败:', error)
  }
}

function closeCardDialog() {
  showAddCard.value = false
  editingCard.value = null
  Object.assign(cardForm, {
    headline: '',
    content: '',
    category_id: categories.value[0]?.id || null,
    type: 2,
    is_repeat: 0
  })
}

async function saveCard() {
  if (!cardForm.headline.trim()) {
    ElMessage.warning('请输入卡片标题')
    return
  }
  if (!cardForm.category_id) {
    ElMessage.warning('请选择分类')
    return
  }
  
  try {
    if (editingCard.value) {
      await cardApi.updateCard(editingCard.value.id, cardForm)
      ElMessage.success('更新成功')
    } else {
      await cardApi.createCard(cardForm)
      ElMessage.success('创建成功')
    }
    closeCardDialog()
    await fetchCards()
    await fetchStats()
  } catch (error) {
    console.error('保存失败:', error)
  }
}

function handleCardAction(action, card) {
  if (action === 'edit') {
    editingCard.value = card
    Object.assign(cardForm, {
      headline: card.headline,
      content: card.content,
      category_id: card.category_id,
      type: card.type,
      is_repeat: card.is_repeat
    })
    showAddCard.value = true
  } else if (action === 'delete') {
    if (confirm('确定删除这个卡片吗？')) {
      deleteCard(card)
    }
  }
}

async function deleteCard(card) {
  try {
    await cardApi.deleteCard(card.id)
    ElMessage.success('删除成功')
    await fetchCards()
    await fetchStats()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

async function startCard(card) {
  try {
    await cardApi.startCard(card.id)
    ElMessage.success('任务已开始')
    await fetchCards()
    await fetchStats()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function stopCard(card) {
  try {
    const res = await cardApi.stopCard(card.id)
    ElMessage.success(`任务已暂停，本次用时 ${formatTime(res.data.elapsed)}`)
    await fetchCards()
    await fetchStats()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function completeCard(card) {
  try {
    await cardApi.completeCard(card.id)
    ElMessage.success('任务已完成')
    await fetchCards()
    await fetchStats()
  } catch (error) {
    console.error('完成失败:', error)
  }
}

async function reopenCard(card) {
  try {
    await cardApi.reopenCard(card.id)
    ElMessage.success('任务已重新打开')
    await fetchCards()
    await fetchStats()
  } catch (error) {
    console.error('重新打开失败:', error)
  }
}

onMounted(async () => {
  await fetchCategories()
  await fetchCards()
  await fetchStats()
})
</script>

<style scoped>
.cards-page {
  padding: 20px 0;
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #fff;
}

.bg-blue { background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%); }
.bg-orange { background: linear-gradient(135deg, #e6a23c 0%, #f0c78a 100%); }
.bg-green { background: linear-gradient(135deg, #67c23a 0%, #95d475 100%); }
.bg-purple { background: linear-gradient(135deg, #9b59b6 0%, #c39bd3 100%); }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  min-height: 300px;
}

.task-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
  border-left: 4px solid #409eff;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.task-card.in-progress {
  border-left-color: #e6a23c;
  background: linear-gradient(135deg, #fff 0%, #fff9e6 100%);
}

.task-card.done {
  border-left-color: #67c23a;
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.more-icon {
  cursor: pointer;
  color: #909399;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.task-card.done .card-title {
  text-decoration: line-through;
}

.card-content {
  font-size: 14px;
  color: #606266;
  margin: 0 0 12px;
  line-height: 1.5;
}

.card-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  font-size: 12px;
  color: #909399;
}

.time-badge, .date-badge {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.form-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
