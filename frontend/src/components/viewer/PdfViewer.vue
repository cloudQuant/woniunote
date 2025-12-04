<template>
  <div class="pdf-viewer-container">
    <div class="pdf-viewer-toolbar">
      <el-button-group>
        <el-button size="small" @click="prevPage" :disabled="pageNum <= 1">
          <el-icon><ArrowLeft /></el-icon>
          上一页
        </el-button>
        <el-button size="small" @click="nextPage" :disabled="pageNum >= numPages">
          下一页
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-button-group>
      <span class="page-info">
        第 {{ pageNum }} / {{ numPages }} 页
      </span>
      <el-button-group>
        <el-button size="small" @click="zoomOut" :disabled="scale <= 0.5">
          <el-icon><ZoomOut /></el-icon>
        </el-button>
        <el-button size="small" @click="resetZoom">
          {{ Math.round(scale * 100) }}%
        </el-button>
        <el-button size="small" @click="zoomIn" :disabled="scale >= 3">
          <el-icon><ZoomIn /></el-icon>
        </el-button>
      </el-button-group>
      <el-button size="small" @click="downloadPdf" v-if="pdfUrl">
        <el-icon><Download /></el-icon>
        下载
      </el-button>
    </div>
    <div class="pdf-viewer-content" ref="viewerRef">
      <canvas ref="canvasRef"></canvas>
    </div>
    <div v-if="loading" class="pdf-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-if="error" class="pdf-error">
      <el-icon><Warning /></el-icon>
      <span>{{ error }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import { ArrowLeft, ArrowRight, ZoomIn, ZoomOut, Download, Loading, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 设置worker路径
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`

const props = defineProps({
  pdfUrl: {
    type: String,
    required: true
  }
})

const canvasRef = ref(null)
const viewerRef = ref(null)
const loading = ref(false)
const error = ref('')
const pageNum = ref(1)
const numPages = ref(0)
const scale = ref(1.5)
let pdfDoc = null

// 渲染PDF页面
async function renderPage(num) {
  if (!pdfDoc || !canvasRef.value) return
  
  try {
    loading.value = true
    error.value = ''
    
    const page = await pdfDoc.getPage(num)
    const viewport = page.getViewport({ scale: scale.value })
    
    const canvas = canvasRef.value
    const context = canvas.getContext('2d')
    
    canvas.height = viewport.height
    canvas.width = viewport.width
    
    const renderContext = {
      canvasContext: context,
      viewport: viewport
    }
    
    await page.render(renderContext).promise
    pageNum.value = num
    loading.value = false
  } catch (err) {
    console.error('Render page error:', err)
    error.value = '渲染页面失败'
    loading.value = false
  }
}

// 加载PDF
async function loadPdf() {
  try {
    loading.value = true
    error.value = ''
    
    // 构建完整URL
    const url = props.pdfUrl.startsWith('http') 
      ? props.pdfUrl 
      : `${import.meta.env.VITE_API_BASE_URL || ''}${props.pdfUrl}`
    
    const loadingTask = pdfjsLib.getDocument({
      url: url,
      withCredentials: false
    })
    
    pdfDoc = await loadingTask.promise
    numPages.value = pdfDoc.numPages
    
    await renderPage(1)
  } catch (err) {
    console.error('Load PDF error:', err)
    error.value = '加载PDF失败，请检查文件是否存在'
    loading.value = false
  }
}

// 上一页
function prevPage() {
  if (pageNum.value <= 1) return
  renderPage(pageNum.value - 1)
}

// 下一页
function nextPage() {
  if (pageNum.value >= numPages.value) return
  renderPage(pageNum.value + 1)
}

// 缩放
function zoomIn() {
  if (scale.value >= 3) return
  scale.value = Math.min(scale.value + 0.25, 3)
  renderPage(pageNum.value)
}

function zoomOut() {
  if (scale.value <= 0.5) return
  scale.value = Math.max(scale.value - 0.25, 0.5)
  renderPage(pageNum.value)
}

function resetZoom() {
  scale.value = 1.5
  renderPage(pageNum.value)
}

// 下载PDF
function downloadPdf() {
  const link = document.createElement('a')
  link.href = props.pdfUrl.startsWith('http') 
    ? props.pdfUrl 
    : `${import.meta.env.VITE_API_BASE_URL || ''}${props.pdfUrl}`
  link.download = ''
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 监听URL变化
watch(() => props.pdfUrl, () => {
  if (props.pdfUrl) {
    loadPdf()
  }
})

onMounted(() => {
  if (props.pdfUrl) {
    loadPdf()
  }
})

onBeforeUnmount(() => {
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }
})
</script>

<style scoped>
.pdf-viewer-container {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #f5f7fa;
  position: relative;
  min-height: 600px;
}

.pdf-viewer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 15px;
  background: #fff;
  border-bottom: 1px solid #dcdfe6;
  border-radius: 4px 4px 0 0;
  flex-wrap: wrap;
  gap: 10px;
}

.page-info {
  font-size: 14px;
  color: #606266;
  margin: 0 10px;
}

.pdf-viewer-content {
  width: 100%;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 20px;
  background: #525252;
  min-height: 600px;
}

.pdf-viewer-content canvas {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  background: #fff;
}

.pdf-loading,
.pdf-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #909399;
  font-size: 14px;
}

.pdf-error {
  color: #f56c6c;
}

@media (max-width: 768px) {
  .pdf-viewer-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .page-info {
    text-align: center;
    margin: 10px 0;
  }
}
</style>

