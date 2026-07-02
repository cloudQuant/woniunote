<template>
  <div class="write-article-page">
    <div class="editor-container">
      <h2 class="page-title">{{ isEdit ? '编辑文章' : '写文章' }}</h2>
      
      <el-form 
        ref="formRef"
        :model="form" 
        :rules="rules" 
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
                  <img v-if="form.thumbnail" :src="form.thumbnail" class="thumbnail-preview" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useArticleStore } from '@/stores/article'
import { articleApi, uploadApi } from '@/api'
import UEditor from '@/components/editor/UEditor.vue'

const route = useRoute()
const router = useRouter()
const articleStore = useArticleStore()

const formRef = ref(null)
const saving = ref(false)
const publishing = ref(false)

const isEdit = computed(() => !!route.params.id)

// UEditor 配置
const editorConfig = {
  initialFrameHeight: 450,
  autoHeightEnabled: true,
  autoFloatEnabled: false,
  maximumWords: 100000
}

// 编辑器就绪回调
function onEditorReady(editor) {
  console.log('UEditor ready:', editor)
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
    const res = await uploadApi.uploadImage(file)
    form.thumbnail = res.data.url
    ElMessage.success('上传成功')
  } catch (error) {
    console.error('上传失败:', error)
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
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const action = form.drafted === 1 ? 'saving' : 'publishing'
  if (action === 'saving') {
    saving.value = true
  } else {
    publishing.value = true
  }
  
  try {
    const data = {
      headline: form.headline,
      type: form.type,
      content: form.content,
      thumbnail: form.thumbnail,
      credit: form.credit,
      drafted: form.drafted
    }
    
    if (isEdit.value) {
      const res = await articleApi.update(route.params.id, data)
      ElMessage.success('更新成功')
      const targetId = res?.data?.articleid || route.params.id
      if (targetId) {
        router.push({ name: 'ArticleDetail', params: { id: targetId } })
      }
    } else {
      const res = await articleApi.create(data)
      ElMessage.success(form.drafted === 1 ? '草稿已保存' : '发布成功')
      router.push({ name: 'ArticleDetail', params: { id: res.data.articleid } })
    }
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
    publishing.value = false
  }
}

async function fetchArticle() {
  if (!isEdit.value) return
  
  try {
    const res = await articleApi.getDetail(route.params.id)
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
    ElMessage.error('文章不存在')
    router.push({ name: 'Home' })
  }
}

onMounted(async () => {
  await articleStore.fetchArticleTypes()
  await fetchArticle()
})
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
