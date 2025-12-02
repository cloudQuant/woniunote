<template>
  <div class="todo-page">
    <div class="container">
      <div class="page-header">
        <h1>待办事项</h1>
        <div class="header-actions">
          <el-button type="primary" @click="showAddCategory = true">
            <el-icon><FolderAdd /></el-icon> 新建分类
          </el-button>
        </div>
      </div>
      
      <el-row :gutter="20">
        <!-- 侧边栏 - 分类列表 -->
        <el-col :span="6" :xs="24">
          <div class="sidebar-card">
            <div class="stats-summary">
              <div class="stat-item">
                <span class="stat-value">{{ stats.total }}</span>
                <span class="stat-label">总计</span>
              </div>
              <div class="stat-item">
                <span class="stat-value text-success">{{ stats.done }}</span>
                <span class="stat-label">已完成</span>
              </div>
              <div class="stat-item">
                <span class="stat-value text-warning">{{ stats.pending }}</span>
                <span class="stat-label">待完成</span>
              </div>
            </div>
            
            <el-menu
              :default-active="String(currentCategory)"
              @select="selectCategory"
            >
              <el-menu-item index="all">
                <el-icon><List /></el-icon>
                <span>全部</span>
              </el-menu-item>
              <el-menu-item 
                v-for="cat in categories" 
                :key="cat.id"
                :index="String(cat.id)"
              >
                <el-icon><Folder /></el-icon>
                <span>{{ cat.name }}</span>
                <el-dropdown class="category-actions" @command="handleCategoryAction($event, cat)">
                  <el-icon class="more-icon"><MoreFilled /></el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </el-menu-item>
            </el-menu>
          </div>
        </el-col>
        
        <!-- 主内容区 - 待办列表 -->
        <el-col :span="18" :xs="24">
          <div class="main-card">
            <!-- 添加待办输入框 -->
            <div class="add-item-form">
              <el-input 
                v-model="newItemBody" 
                placeholder="添加新的待办事项，按 Enter 确认"
                @keyup.enter="addItem"
                size="large"
              >
                <template #prepend>
                  <el-select v-model="newItemCategory" placeholder="分类" style="width: 120px">
                    <el-option 
                      v-for="cat in categories" 
                      :key="cat.id" 
                      :label="cat.name" 
                      :value="cat.id" 
                    />
                  </el-select>
                </template>
                <template #append>
                  <el-button @click="addItem" :disabled="!newItemBody.trim()">
                    <el-icon><Plus /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </div>
            
            <!-- 筛选 -->
            <div class="filter-bar">
              <el-radio-group v-model="filterDone" @change="fetchItems">
                <el-radio-button :value="null">全部</el-radio-button>
                <el-radio-button :value="0">待完成</el-radio-button>
                <el-radio-button :value="1">已完成</el-radio-button>
              </el-radio-group>
            </div>
            
            <!-- 待办列表 -->
            <div class="todo-list" v-loading="loading">
              <div 
                v-for="item in items" 
                :key="item.id" 
                class="todo-item"
                :class="{ done: item.done }"
              >
                <el-checkbox 
                  :model-value="item.done === 1" 
                  @change="toggleItem(item)"
                />
                <div class="item-content">
                  <span class="item-body" :class="{ 'line-through': item.done }">
                    {{ item.body }}
                  </span>
                  <div class="item-meta">
                    <el-tag size="small" v-if="item.priority === 2" type="danger">紧急</el-tag>
                    <el-tag size="small" v-else-if="item.priority === 1" type="warning">重要</el-tag>
                    <span class="item-time">{{ formatDate(item.createtime) }}</span>
                  </div>
                </div>
                <div class="item-actions">
                  <el-button size="small" text @click="editItem(item)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-popconfirm title="确定删除？" @confirm="deleteItem(item)">
                    <template #reference>
                      <el-button size="small" text type="danger">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
              
              <el-empty v-if="!loading && items.length === 0" description="暂无待办事项" />
            </div>
            
            <!-- 分页 -->
            <div class="pagination" v-if="total > pageSize">
              <el-pagination
                v-model:current-page="currentPage"
                :page-size="pageSize"
                :total="total"
                layout="prev, pager, next"
                @current-change="fetchItems"
              />
            </div>
          </div>
        </el-col>
      </el-row>
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
    
    <!-- 编辑事项对话框 -->
    <el-dialog v-model="showEditItem" title="编辑待办" width="500px">
      <el-form v-if="editingItem">
        <el-form-item label="内容">
          <el-input v-model="editingItem.body" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="editingItem.priority">
            <el-option :value="0" label="普通" />
            <el-option :value="1" label="重要" />
            <el-option :value="2" label="紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editingItem.category_id">
            <el-option 
              v-for="cat in categories" 
              :key="cat.id" 
              :label="cat.name" 
              :value="cat.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditItem = false">取消</el-button>
        <el-button type="primary" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  List, Folder, FolderAdd, Plus, Edit, Delete, MoreFilled 
} from '@element-plus/icons-vue'
import { todoApi } from '@/api'

// 分类相关
const categories = ref([])
const currentCategory = ref('all')
const showAddCategory = ref(false)
const newCategoryName = ref('')

// 待办事项相关
const items = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)
const filterDone = ref(null)

// 新增事项
const newItemBody = ref('')
const newItemCategory = ref(null)

// 编辑事项
const showEditItem = ref(false)
const editingItem = ref(null)

// 统计
const stats = reactive({ total: 0, done: 0, pending: 0 })

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function fetchCategories() {
  try {
    const res = await todoApi.getCategories()
    categories.value = res.data
    if (categories.value.length > 0 && !newItemCategory.value) {
      newItemCategory.value = categories.value[0].id
    }
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

async function fetchItems() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (currentCategory.value !== 'all') {
      params.category_id = currentCategory.value
    }
    if (filterDone.value !== null) {
      params.done = filterDone.value
    }
    
    const res = await todoApi.getItems(params)
    items.value = res.data
    total.value = res.total
  } catch (error) {
    console.error('获取待办失败:', error)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await todoApi.getStats()
    Object.assign(stats, res.data)
  } catch (error) {
    console.error('获取统计失败:', error)
  }
}

function selectCategory(key) {
  currentCategory.value = key === 'all' ? 'all' : parseInt(key)
  currentPage.value = 1
  fetchItems()
}

async function addCategory() {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  try {
    await todoApi.createCategory({ name: newCategoryName.value })
    ElMessage.success('创建成功')
    showAddCategory.value = false
    newCategoryName.value = ''
    await fetchCategories()
  } catch (error) {
    console.error('创建分类失败:', error)
  }
}

async function handleCategoryAction(action, cat) {
  if (action === 'edit') {
    const newName = prompt('编辑分类名称', cat.name)
    if (newName && newName !== cat.name) {
      try {
        await todoApi.updateCategory(cat.id, { name: newName })
        ElMessage.success('更新成功')
        await fetchCategories()
      } catch (error) {
        console.error('更新失败:', error)
      }
    }
  } else if (action === 'delete') {
    if (confirm('确定删除该分类吗？分类下的待办事项也会被删除')) {
      try {
        await todoApi.deleteCategory(cat.id)
        ElMessage.success('删除成功')
        if (currentCategory.value === cat.id) {
          currentCategory.value = 'all'
        }
        await fetchCategories()
        await fetchItems()
        await fetchStats()
      } catch (error) {
        console.error('删除失败:', error)
      }
    }
  }
}

async function addItem() {
  if (!newItemBody.value.trim()) return
  if (!newItemCategory.value) {
    ElMessage.warning('请先选择分类')
    return
  }
  
  try {
    await todoApi.createItem({
      body: newItemBody.value,
      category_id: newItemCategory.value
    })
    ElMessage.success('添加成功')
    newItemBody.value = ''
    await fetchItems()
    await fetchStats()
  } catch (error) {
    console.error('添加失败:', error)
  }
}

async function toggleItem(item) {
  try {
    await todoApi.toggleItem(item.id)
    await fetchItems()
    await fetchStats()
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

function editItem(item) {
  editingItem.value = { ...item }
  showEditItem.value = true
}

async function saveItem() {
  try {
    await todoApi.updateItem(editingItem.value.id, {
      body: editingItem.value.body,
      priority: editingItem.value.priority,
      category_id: editingItem.value.category_id
    })
    ElMessage.success('保存成功')
    showEditItem.value = false
    await fetchItems()
  } catch (error) {
    console.error('保存失败:', error)
  }
}

async function deleteItem(item) {
  try {
    await todoApi.deleteItem(item.id)
    ElMessage.success('删除成功')
    await fetchItems()
    await fetchStats()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

onMounted(async () => {
  await fetchCategories()
  await fetchItems()
  await fetchStats()
})
</script>

<style scoped>
.todo-page {
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

.sidebar-card, .main-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.stats-summary {
  display: flex;
  justify-content: space-around;
  padding: 15px 0;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 15px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-value.text-success { color: #67c23a; }
.stat-value.text-warning { color: #e6a23c; }

.stat-label {
  font-size: 12px;
  color: #909399;
}

.category-actions {
  margin-left: auto;
}

.more-icon {
  opacity: 0;
  transition: opacity 0.3s;
}

.el-menu-item:hover .more-icon {
  opacity: 1;
}

.add-item-form {
  margin-bottom: 20px;
}

.filter-bar {
  margin-bottom: 15px;
}

.todo-list {
  min-height: 300px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  padding: 12px 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
  transition: all 0.3s;
}

.todo-item:hover {
  background: #ebeef5;
}

.todo-item.done {
  opacity: 0.6;
}

.item-content {
  flex: 1;
  margin-left: 12px;
}

.item-body {
  display: block;
  font-size: 15px;
  color: #303133;
  line-height: 1.5;
}

.item-body.line-through {
  text-decoration: line-through;
  color: #909399;
}

.item-meta {
  margin-top: 5px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.item-time {
  font-size: 12px;
  color: #909399;
}

.item-actions {
  display: flex;
  gap: 5px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .sidebar-card {
    margin-bottom: 20px;
  }
}
</style>
