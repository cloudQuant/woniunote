<template>
  <div class="category-manager">
    <div class="category-toolbar">
      <h2>文章菜单分类</h2>
      <div class="category-actions">
        <el-button :icon="Refresh" @click="loadCategories" :loading="loading">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate()">新增顶级分类</el-button>
      </div>
    </div>

    <el-table :data="flatRows" row-key="id" stripe v-loading="loading">
      <el-table-column label="名称" min-width="220">
        <template #default="{ row }">
          <span class="category-name" :style="{ paddingLeft: `${row.depth * 20}px` }">
            {{ row.name }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="ID" prop="id" width="80" />
      <el-table-column label="父节点" width="120">
        <template #default="{ row }">
          {{ row.parent_id || '顶级' }}
        </template>
      </el-table-column>
      <el-table-column label="排序" prop="sort_order" width="90" />
      <el-table-column label="文章数" prop="article_count" width="90" />
      <el-table-column label="显示" width="90">
        <template #default="{ row }">
          <el-tag :type="row.visible ? 'success' : 'info'" size="small">
            {{ row.visible ? '显示' : '隐藏' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :icon="Plus" @click="openCreate(row)">子分类</el-button>
          <el-button size="small" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" :icon="row.visible ? Hide : View" @click="toggleVisible(row)">
            {{ row.visible ? '隐藏' : '显示' }}
          </el-button>
          <el-button size="small" type="danger" :icon="Delete" @click="requestDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="editorVisible" :title="editingId ? '编辑分类' : '新增分类'" width="520px">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="父节点">
          <el-select v-model="editForm.parent_id" filterable style="width: 100%;">
            <el-option
              v-for="option in parentOptions"
              :key="option.id"
              :label="option.label"
              :value="option.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="公开导航显示">
          <el-switch v-model="editForm.visible" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCategory" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteVisible" title="删除分类" width="520px">
      <p class="delete-copy">
        分类「{{ deleteTarget?.name }}」下有 {{ deleteTarget?.article_count || 0 }} 篇文章，请选择迁移目标分类。
      </p>
      <el-select v-model="moveArticlesTo" filterable placeholder="请选择迁移目标" style="width: 100%;">
        <el-option
          v-for="option in replacementOptions"
          :key="option.id"
          :label="option.label"
          :value="option.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="deleteVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDeleteWithMove" :loading="deleting">删除并迁移</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Hide, Plus, Refresh, View } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const emit = defineEmits(['changed'])

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const categoriesTree = ref([])
const categoriesFlat = ref([])
const editorVisible = ref(false)
const deleteVisible = ref(false)
const editingId = ref(null)
const deleteTarget = ref(null)
const moveArticlesTo = ref(null)

const editForm = reactive({
  name: '',
  parent_id: 0,
  sort_order: 0,
  visible: true
})

const flatRows = computed(() => flattenRows(categoriesTree.value))

const parentOptions = computed(() => {
  const options = [{ id: 0, label: '顶级分类' }]
  for (const row of flatRows.value) {
    if (editingId.value && (row.id === editingId.value || isDescendant(row.id, editingId.value))) {
      continue
    }
    options.push({
      id: row.id,
      label: `${'　'.repeat(row.depth)}${row.name}`
    })
  }
  return options
})

const replacementOptions = computed(() => {
  if (!deleteTarget.value) return []
  return flatRows.value
    .filter((row) => row.id !== deleteTarget.value.id && !isDescendant(row.id, deleteTarget.value.id))
    .map((row) => ({
      id: row.id,
      label: `${'　'.repeat(row.depth)}${row.name}`
    }))
})

function flattenRows(nodes, depth = 0) {
  const rows = []
  for (const node of nodes || []) {
    rows.push({
      ...node,
      depth,
      visible: node.visible !== 0
    })
    rows.push(...flattenRows(node.children || [], depth + 1))
  }
  return rows
}

function isDescendant(candidateId, ancestorId) {
  const byId = new Map(categoriesFlat.value.map((item) => [item.id, item]))
  let current = byId.get(candidateId)
  const seen = new Set()
  while (current?.parent_id && !seen.has(current.id)) {
    seen.add(current.id)
    if (current.parent_id === ancestorId) return true
    current = byId.get(current.parent_id)
  }
  return false
}

async function loadCategories() {
  loading.value = true
  try {
    const res = await adminApi.getArticleCategories()
    categoriesTree.value = res.data.tree || []
    categoriesFlat.value = res.data.flat || []
  } catch (error) {
    ElMessage.error(error.message || '获取分类失败')
  } finally {
    loading.value = false
  }
}

function openCreate(parent = null) {
  editingId.value = null
  editForm.name = ''
  editForm.parent_id = parent?.id || 0
  editForm.sort_order = 0
  editForm.visible = true
  editorVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  editForm.name = row.name
  editForm.parent_id = row.parent_id || 0
  editForm.sort_order = row.sort_order || 0
  editForm.visible = row.visible !== 0
  editorVisible.value = true
}

function buildPayload() {
  return {
    name: editForm.name.trim(),
    parent_id: editForm.parent_id || null,
    sort_order: editForm.sort_order || 0,
    visible: editForm.visible ? 1 : 0
  }
}

async function reloadAfterMutation(message) {
  ElMessage.success(message)
  await loadCategories()
  emit('changed')
}

async function saveCategory() {
  const payload = buildPayload()
  if (!payload.name) {
    ElMessage.error('分类名称不能为空')
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      await adminApi.updateArticleCategory(editingId.value, payload)
      editorVisible.value = false
      await reloadAfterMutation('分类已更新')
    } else {
      await adminApi.createArticleCategory(payload)
      editorVisible.value = false
      await reloadAfterMutation('分类已创建')
    }
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleVisible(row) {
  try {
    await adminApi.updateArticleCategory(row.id, { visible: row.visible ? 0 : 1 })
    await reloadAfterMutation(row.visible ? '分类已隐藏' : '分类已显示')
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function requestDelete(row) {
  deleteTarget.value = row
  moveArticlesTo.value = null

  if ((row.article_count || 0) > 0) {
    deleteVisible.value = true
    return
  }

  try {
    await ElMessageBox.confirm(`确定要删除分类「${row.name}」吗？`, '删除确认', { type: 'warning' })
    await performDelete(row.id, {})
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function confirmDeleteWithMove() {
  if (!moveArticlesTo.value) {
    ElMessage.error('请选择迁移目标分类')
    return
  }
  await performDelete(deleteTarget.value.id, { move_articles_to: moveArticlesTo.value })
}

async function performDelete(id, params) {
  deleting.value = true
  try {
    await adminApi.deleteArticleCategory(id, params)
    deleteVisible.value = false
    await reloadAfterMutation('分类已删除')
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(loadCategories)
</script>

<style scoped>
.category-manager {
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  padding: 20px;
  box-shadow: var(--wn-shadow-card);
}

.category-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.category-toolbar h2 {
  margin: 0;
  font-size: 18px;
  color: var(--wn-color-text);
}

.category-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.category-name {
  display: inline-block;
  font-weight: 500;
  color: var(--wn-color-text);
}

.delete-copy {
  margin: 0 0 12px;
  color: var(--wn-color-text-secondary);
}

@media (max-width: 768px) {
  .category-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .category-actions {
    flex-wrap: wrap;
  }
}
</style>
