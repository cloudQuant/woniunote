<template>
  <div class="pdf-viewer-container" ref="containerRef">
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
        <el-button size="small" @click="fitWidth" :type="fitMode === 'width' ? 'primary' : 'default'">
          适应宽度
        </el-button>
        <el-button size="small" @click="zoomIn" :disabled="scale >= 5">
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
/**
 * @component PdfViewer
 * @description PDF 文件预览组件
 * 基于 pdf.js 实现，支持翻页、缩放、适应宽度和下载功能。
 */
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import { ArrowLeft, ArrowRight, ZoomIn, ZoomOut, Download, Loading, Warning } from '@element-plus/icons-vue'

// 设置 worker 路径
// 使用 Vite 的 ?raw 将 worker 内容作为字符串导入，然后创建 Blob URL
// 这样可以避免跨域和 MIME 类型问题
import pdfWorkerContent from 'pdfjs-dist/build/pdf.worker.min.mjs?raw'

const workerBlob = new Blob([pdfWorkerContent], { type: 'text/javascript' })
const workerUrl = URL.createObjectURL(workerBlob)

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps({
  /**
   * PDF 文件 URL
   */
  pdfUrl: {
    type: String,
    required: true
  }
})

const canvasRef = ref(null)
const viewerRef = ref(null)
const containerRef = ref(null)
const loading = ref(false)
const error = ref('')
const pageNum = ref(1)
const numPages = ref(0)
const scale = ref(1)
const fitMode = ref('width') // 'width' 或 'manual'
let pdfDoc = null
let currentPage = null // 缓存当前页面对象

/**
 * 计算适应宽度的缩放比例
 * @param {Object} page - PDF 页面对象
 * @returns {number} 缩放比例
 */
function calculateFitWidthScale(page) {
  if (!viewerRef.value) return 1
  
  // 获取容器宽度（减去padding）
  const containerWidth = viewerRef.value.clientWidth - 40
  
  // 获取页面原始尺寸（scale=1）
  const viewport = page.getViewport({ scale: 1 })
  
  // 计算缩放比例使页面宽度适应容器
  const fitScale = containerWidth / viewport.width
  
  return Math.min(fitScale, 3) // 最大缩放3倍
}

/**
 * 渲染指定页码的 PDF 页面
 * @param {number} num - 页码
 */
async function renderPage(num) {
  if (!pdfDoc || !canvasRef.value) return
  
  try {
    loading.value = true
    error.value = ''
    
    const page = await pdfDoc.getPage(num)
    currentPage = page
    
    // 如果是适应宽度模式，自动计算缩放比例
    if (fitMode.value === 'width') {
      scale.value = calculateFitWidthScale(page)
    }
    
    const viewport = page.getViewport({ scale: scale.value })
    
    const canvas = canvasRef.value
    const context = canvas.getContext('2d')
    
    // 使用设备像素比提高清晰度
    const pixelRatio = window.devicePixelRatio || 1
    canvas.height = viewport.height * pixelRatio
    canvas.width = viewport.width * pixelRatio
    canvas.style.height = viewport.height + 'px'
    canvas.style.width = viewport.width + 'px'
    
    context.scale(pixelRatio, pixelRatio)
    
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

/**
 * 加载 PDF 文档
 */
async function loadPdf() {
  try {
    loading.value = true
    error.value = ''
    
    // 构建完整URL - 使用当前页面的origin确保正确的域名和端口
    let url = props.pdfUrl
    if (!url.startsWith('http')) {
      url = `${window.location.origin}${url}`
    }
    
    console.log('Loading PDF from:', url)
    
    const loadingTask = pdfjsLib.getDocument({
      url: url,
      withCredentials: false
    })
    
    pdfDoc = await loadingTask.promise
    numPages.value = pdfDoc.numPages
    console.log('PDF loaded successfully, pages:', numPages.value)
    
    await renderPage(1)
  } catch (err) {
    console.error('Load PDF error:', err)
    error.value = '加载PDF失败: ' + (err.message || '请检查文件是否存在')
    loading.value = false
  }
}

/**
 * 上一页
 */
function prevPage() {
  if (pageNum.value <= 1) return
  renderPage(pageNum.value - 1)
}

/**
 * 下一页
 */
function nextPage() {
  if (pageNum.value >= numPages.value) return
  renderPage(pageNum.value + 1)
}

/**
 * 放大
 */
function zoomIn() {
  fitMode.value = 'manual'
  if (scale.value >= 5) return
  scale.value = Math.min(scale.value + 0.25, 5)
  renderPage(pageNum.value)
}

/**
 * 缩小
 */
function zoomOut() {
  fitMode.value = 'manual'
  if (scale.value <= 0.5) return
  scale.value = Math.max(scale.value - 0.25, 0.5)
  renderPage(pageNum.value)
}

/**
 * 适应宽度模式
 */
function fitWidth() {
  fitMode.value = 'width'
  renderPage(pageNum.value)
}

/**
 * 下载 PDF 文件
 */
function downloadPdf() {
  let url = props.pdfUrl
  if (!url.startsWith('http')) {
    url = `${window.location.origin}${url}`
  }
  const link = document.createElement('a')
  link.href = url
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
  
  // 监听窗口大小变化，重新计算适应宽度
  window.addEventListener('resize', handleResize)
})

function handleResize() {
  if (fitMode.value === 'width' && pdfDoc) {
    renderPage(pageNum.value)
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
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
