<template>
  <div class="write-article-page">
    <div class="editor-container">
      <h2 class="page-title">{{ isEdit ? '编辑文章' : '写文章' }}</h2>
      
      <el-form 
        ref="formRef"
        :model="form" 
        :rules="rules" 
        :disabled="!editorOwnerReady || editorOwnerChanged"
        :inert="!editorOwnerReady || editorOwnerChanged"
        label-position="top"
      >
        <el-form-item label="标题" prop="headline">
          <el-input 
            v-model="form.headline" 
            placeholder="请输入文章标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <div class="editor-wrapper">
            <UEditor
              ref="editorRef"
              v-model="form.content"
              :config="editorConfig"
              @ready="onEditorReady"
            />
          </div>
        </el-form-item>
        
        <el-row :gutter="20" class="meta-row">
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="分类" prop="type" class="meta-item">
              <el-cascader
                v-model="form.typeArray"
                :options="categoryOptions"
                placeholder="请选择分类"
                @change="onTypeChange"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="积分" class="meta-item">
              <el-input-number 
                v-model="form.credit" 
                :min="0" 
                :max="100"
                placeholder="阅读所需积分"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="8">
            <el-form-item label="缩略图" class="meta-item">
              <div class="thumbnail-box">
                <el-upload
                  class="thumbnail-uploader"
                  :show-file-list="false"
                  :http-request="uploadThumbnail"
                  accept="image/*"
                >
                  <img v-if="thumbnailPreviewUrl" :src="thumbnailPreviewUrl" class="thumbnail-preview" />
                  <el-icon v-else class="upload-icon"><Plus /></el-icon>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item>
          <div class="form-actions">
            <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
            <el-button type="primary" @click="publish" :loading="publishing">
              {{ isEdit ? '更新' : '发布' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
/**
 * @component WriteArticle
 * @description 文章编辑/发布页面组件
 * 提供富文本编辑器（UEditor）用于撰写文章，支持设置标题、分类、积分、缩略图等元数据。
 * 支持保存草稿和发布文章，同时处理新建和编辑模式。
 */
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useArticleStore } from '@/stores/article'
import { useUserStore } from '@/stores/user'
import { logInfo, logWarning } from '@/utils/logger'
import { articleApi, uploadApi } from '@/api'
import { notifyError } from '@/utils/errorToast'
import {
  isValidArticleThumbnail,
  resolveArticleThumbnailUrl
} from '@/utils/articleThumbnail'
import {
  clearEditorRecovery,
  readEditorRecovery,
  registerEditorSnapshotProvider,
  saveEditorRecovery
} from '@/utils/editorRecovery'
import UEditor from '@/components/editor/UEditor.vue'

const route = useRoute()
const router = useRouter()
const articleStore = useArticleStore()
const userStore = useUserStore()

const formRef = ref(null)
const editorRef = ref(null)
const saving = ref(false)
const publishing = ref(false)
const editorOwnerChanged = ref(false)
const editorOwnerReady = ref(false)

const isEdit = computed(() => !!route.params.id)

// UEditor 配置
const editorConfig = {
  initialFrameHeight: 450,
  autoHeightEnabled: true,
  autoFloatEnabled: false,
  maximumWords: 100000
}

// 编辑器就绪回调
function onEditorReady() {
  logInfo('UEditor ready')
}

const form = reactive({
  headline: '',
  type: null,
  typeArray: [],
  content: '',
  thumbnail: '',
  credit: 0,
  drafted: 0
})

const thumbnailPreviewUrl = computed(() => resolveArticleThumbnailUrl(
  form.thumbnail,
  form.type,
  { fallbackForEmpty: false }
))

const recoveryPath = route.fullPath || route.path || '/write'
let editorOwnerSnapshot = null
let editorOwnerKey = ''
let recoveryOwnerId = null
let editorOwnerInitialization = null
let editorQuarantinePromise = Promise.resolve()
let unregisterEditorSnapshot = () => {}

function getSessionOwnerKey(snapshot) {
  return JSON.stringify([snapshot?.epoch || '', snapshot?.userIdentity || null])
}

function getEditorDraft() {
  // The form stays disabled until the article and any prior recovery snapshot
  // finish loading. Never replace a saved draft with this initial placeholder.
  if (!editorOwnerReady.value) return null

  // Flush UEditor’s debounce before copying the form so the recovery snapshot
  // includes the latest iframe content when a 401 redirects away from this page.
  editorRef.value?.flushContent?.()
  return {
    headline: form.headline,
    type: form.type,
    typeArray: [...form.typeArray],
    content: form.content,
    thumbnail: form.thumbnail,
    credit: form.credit,
    drafted: form.drafted
  }
}

function clearEditorForm() {
  Object.assign(form, {
    headline: '',
    type: null,
    typeArray: [],
    content: '',
    thumbnail: '',
    credit: 0,
    drafted: 0
  })
  formRef.value?.clearValidate?.()
}

function warnEditorRecovery(message, error) {
  logWarning('编辑恢复数据处理失败', { message: error?.message || '未知错误' })
  try {
    ElMessage.warning(message)
  } catch (messageError) {
    logWarning('无法显示编辑恢复失败提示', {
      message: messageError?.message || '未知错误'
    })
  }
}

function bindEditorToCurrentSession(snapshot) {
  editorOwnerSnapshot = snapshot
  editorOwnerKey = getSessionOwnerKey(snapshot)
  recoveryOwnerId = snapshot.userId
  unregisterEditorSnapshot()
  unregisterEditorSnapshot = registerEditorSnapshotProvider(
    recoveryOwnerId,
    getEditorDraft,
    {
      path: recoveryPath,
      shouldPersistOnExit: () => {
        if (!editorOwnerSnapshot || !editorOwnerReady.value || editorOwnerChanged.value) return false
        const currentSnapshot = userStore.captureCredentials()
        return userStore.isSessionCurrent(editorOwnerSnapshot) &&
          getSessionOwnerKey(currentSnapshot) === editorOwnerKey
      },
      onPageExitError: (error) => {
        warnEditorRecovery(
          '离开页面时，本地编辑恢复稿未能保存；页面刷新后可能无法找回',
          error
        )
      }
    }
  )
}

async function initializeEditorOwner() {
  if (editorOwnerSnapshot) return editorOwnerSnapshot
  if (!editorOwnerInitialization) {
    editorOwnerInitialization = (async () => {
      await userStore.syncSession()
      const snapshot = userStore.captureCredentials()
      bindEditorToCurrentSession(snapshot)
      return snapshot
    })()
  }
  return editorOwnerInitialization
}

function quarantineEditorForOwnerChange() {
  if (editorOwnerChanged.value) return editorQuarantinePromise
  editorOwnerChanged.value = true
  editorQuarantinePromise = (async () => {
    try {
      if (recoveryOwnerId !== null && recoveryOwnerId !== undefined) {
        await saveEditorRecovery(recoveryOwnerId, recoveryPath)
      }
    } catch (error) {
      notifyError(error, '账号已切换，无法保存原账号的编辑恢复稿')
    } finally {
      unregisterEditorSnapshot()
      clearEditorForm()
    }
    ElMessage.warning('登录账号已切换，当前编辑已隔离；请使用原账号恢复草稿。')
  })()
  return editorQuarantinePromise
}

watch(
  () => getSessionOwnerKey(userStore.captureCredentials()),
  (nextOwner) => {
    if (editorOwnerSnapshot && nextOwner !== editorOwnerKey) {
      void quarantineEditorForOwnerChange()
    }
  },
  { flush: 'sync' }
)

async function captureBoundSessionForRequest() {
  await initializeEditorOwner()
  await userStore.syncSession()
  const snapshot = userStore.captureCredentials()
  if (editorOwnerChanged.value || getSessionOwnerKey(snapshot) !== editorOwnerKey) {
    await quarantineEditorForOwnerChange()
    return null
  }
  return snapshot
}

async function isBoundSessionCurrent(snapshot) {
  await userStore.syncSession()
  if (editorOwnerChanged.value ||
      getSessionOwnerKey(userStore.captureCredentials()) !== editorOwnerKey) {
    await quarantineEditorForOwnerChange()
    return false
  }
  return userStore.isSessionCurrent(snapshot)
}

const rules = {
  headline: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { max: 100, message: '标题不能超过100个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ],
  content: [
    { required: true, message: '请输入内容', trigger: 'blur' }
  ]
}

const categoryOptions = computed(() => {
  return articleStore.categoryOptions || []
})

function onTypeChange(value) {
  if (value && value.length > 0) {
    form.type = value[value.length - 1]
  } else {
    form.type = null
  }
}

async function uploadThumbnail({ file }) {
  try {
    const snapshot = await captureBoundSessionForRequest()
    if (!snapshot) return
    const res = await uploadApi.uploadImage(file, { _sessionSnapshot: snapshot })
    if (!await isBoundSessionCurrent(snapshot)) return
    if (!isValidArticleThumbnail(res?.data?.url) || !res.data.url) {
      ElMessage.error('上传返回了无效的缩略图路径')
      return
    }
    form.thumbnail = res.data.url
    ElMessage.success('上传成功')
  } catch (error) {
    console.error('上传失败:', error)
    notifyError(error, '上传失败')
  }
}

async function saveDraft() {
  form.drafted = 1
  await saveArticle()
}

async function publish() {
  form.drafted = 0
  await saveArticle()
}

async function saveArticle() {
  if (!formRef.value || editorOwnerChanged.value) return
  if (!isValidArticleThumbnail(form.thumbnail)) {
    ElMessage.error('缩略图路径无效')
    return
  }

  // 提交前冲刷编辑器待同步内容：编辑器输入走 300ms 防抖，用户“输入后立即点击
  // 保存/发布”时防抖可能尚未触发；且 Firefox 在点击 iframe 外部按钮时不一定
  // 派发编辑区 body 的 blur（flush 依赖的另一个入口），校验会读到空的旧值并报
  // “请输入内容”（迭代20 / Epic 20.2：E2E 在 firefox 下偶发复现）。
  editorRef.value?.flushContent?.()

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const action = form.drafted === 1 ? 'saving' : 'publishing'
  if (action === 'saving') {
    saving.value = true
  } else {
    publishing.value = true
  }
  
  try {
    const snapshot = await captureBoundSessionForRequest()
    if (!snapshot) return
    const data = {
      headline: form.headline,
      type: form.type,
      content: form.content,
      thumbnail: form.thumbnail,
      credit: form.credit,
      drafted: form.drafted
    }
    
    if (isEdit.value) {
      const res = await articleApi.update(route.params.id, data, { _sessionSnapshot: snapshot })
      if (!await isBoundSessionCurrent(snapshot)) return
      ElMessage.success('更新成功')
      const targetId = res?.data?.articleid || route.params.id
      if (targetId) {
        router.push({ name: 'ArticleDetail', params: { id: targetId } })
      }
    } else {
      const res = await articleApi.create(data, { _sessionSnapshot: snapshot })
      if (!await isBoundSessionCurrent(snapshot)) return
      ElMessage.success(form.drafted === 1 ? '草稿已保存' : '发布成功')
      router.push({ name: 'ArticleDetail', params: { id: res.data.articleid } })
    }
  } catch (error) {
    console.error('保存失败:', error)
    notifyError(error, '保存失败')
  } finally {
    saving.value = false
    publishing.value = false
  }
}

async function fetchArticle() {
  if (!isEdit.value) return
  
  try {
    const snapshot = await captureBoundSessionForRequest()
    if (!snapshot) return
    const res = await articleApi.getDetail(route.params.id, { _sessionSnapshot: snapshot })
    if (!await isBoundSessionCurrent(snapshot)) return
    const article = res.data
    
    form.headline = article.headline
    form.type = article.type
    form.content = article.content
    form.thumbnail = article.thumbnail
    form.credit = article.credit
    form.drafted = article.drafted
    
    form.typeArray = articleStore.getTypePath(article.type)
  } catch (error) {
    console.error('获取文章失败:', error)
    if (error?.response?.status === 401) return
    ElMessage.error('文章不存在')
    router.push({ name: 'Home' })
  }
}

function restoreEditorRecovery() {
  if (editorOwnerChanged.value) return
  let snapshot
  try {
    snapshot = readEditorRecovery(recoveryOwnerId, recoveryPath)
  } catch (error) {
    warnEditorRecovery(
      '本地编辑恢复稿无法读取，已加载服务器内容；请检查浏览器存储设置',
      error
    )
    return
  }
  if (!snapshot) return

  Object.assign(form, snapshot.draft)
  try {
    clearEditorRecovery(recoveryOwnerId)
  } catch (error) {
    warnEditorRecovery('已恢复未保存内容，但无法清理本地恢复副本', error)
    return
  }
  ElMessage.info?.('已恢复上次未保存的编辑内容')
}

onMounted(async () => {
  await articleStore.fetchArticleTypes()
  try {
    await initializeEditorOwner()
  } catch (error) {
    logWarning('编辑器会话初始化失败，store 已提示并清除内存登录状态', {
      message: error?.message || '未知错误'
    })
    return
  }
  await fetchArticle()
  restoreEditorRecovery()
  editorOwnerReady.value = true
})

onBeforeUnmount(() => unregisterEditorSnapshot())
</script>

<style scoped>
.write-article-page {
  padding: 20px 0;
  background: var(--wn-color-canvas);
  min-height: calc(100vh - 200px);
}

.editor-container {
  max-width: 900px;
  margin: 0 auto;
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  box-shadow: var(--wn-shadow-card);
  padding: 30px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 30px;
  color: var(--wn-color-text);
}

.meta-row {
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
}

.meta-item :deep(.el-form-item__label) {
  margin-bottom: 4px;
}

.meta-item :deep(.el-form-item__content) {
  display: flex;
  align-items: flex-start;
}

.meta-item :deep(.el-input-number),
.meta-item :deep(.el-cascader) {
  width: 220px;
}

.thumbnail-box {
  display: flex;
  justify-content: flex-start;
}

.thumbnail-uploader {
  width: 180px;
  height: 40px;
  border: 1px dashed var(--wn-color-border-strong);
  border-radius: var(--wn-radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.3s;
}

.thumbnail-uploader:hover {
  border-color: var(--wn-color-primary);
}

.thumbnail-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: var(--wn-radius-sm);
}

.upload-icon {
  font-size: 16px;
  color: var(--wn-color-text-muted);
}

.editor-wrapper {
  width: 100%;
}

.form-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}
</style>
