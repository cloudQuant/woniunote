/**
 * @module composables/useArticleRendering
 * @description 文章正文渲染逻辑
 * 负责 MathJax 公式排版，以及将正文中的 PDF 占位符 / PDF 链接替换为
 * 动态挂载的 PdfViewer 组件实例（含应用实例的清理）。
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import PdfViewer from '@/components/viewer/PdfViewer.vue'
import { logInfo } from '@/utils/logger'

/**
 * 文章正文渲染 composable
 * @param {import('vue').Ref<HTMLElement|null>} bodyRef - 正文容器 ref
 * @returns {{renderMathFormulas: Function, replacePdfPlaceholders: Function, cleanupPdfViewers: Function}}
 */
export function useArticleRendering(bodyRef) {
  // 存储创建的PDF查看器应用实例，用于清理
  const pdfViewerApps = []

  /**
   * 渲染数学公式
   * 支持 MathJax 2.x and 3.x
   */
  function renderMathFormulas() {
    if (!bodyRef.value) return

    // 延迟执行确保DOM完全更新
    setTimeout(() => {
      if (window.MathJax) {
        try {
          // MathJax 3.x
          if (window.MathJax.typeset) {
            window.MathJax.typeset([bodyRef.value])
            logInfo('MathJax公式渲染成功')
          }
          // MathJax 2.x
          else if (window.MathJax.Hub) {
            window.MathJax.Hub.Queue(['Typeset', window.MathJax.Hub, bodyRef.value])
          }
        } catch (e) {
          console.error('MathJax渲染失败:', e)
        }
      }
    }, 100)
  }

  /**
   * 在容器节点上动态挂载一个 PDF 查看器应用实例
   * @param {HTMLElement} container - 挂载容器
   * @param {string} pdfUrl - PDF 文件地址
   */
  function mountPdfViewer(container, pdfUrl) {
    // 创建Vue应用实例并挂载PDF查看器组件，注入ElementPlus
    const app = createApp(PdfViewer, { pdfUrl })
    app.use(ElementPlus)
    app.mount(container)
    pdfViewerApps.push(app)
  }

  /**
   * 清理所有已挂载的 PDF 查看器应用实例
   */
  function cleanupPdfViewers() {
    pdfViewerApps.forEach(app => {
      try { app.unmount() } catch { /* already unmounted, ignore */ }
    })
    pdfViewerApps.length = 0
  }

  /**
   * 替换文章内容中的PDF占位符为PDF查看器组件
   * 动态挂载 Vue 组件到 DOM 节点
   */
  function replacePdfPlaceholders() {
    if (!bodyRef.value) return

    // 清理之前创建的应用实例
    cleanupPdfViewers()

    // 查找所有PDF占位符
    const placeholders = bodyRef.value.querySelectorAll('.pdf-viewer-placeholder')
    logInfo('Found PDF placeholders', { count: placeholders.length })

    placeholders.forEach((placeholder) => {
      const pdfUrl = placeholder.getAttribute('data-pdf-url')
      logInfo('PDF URL', { url: pdfUrl })
      if (!pdfUrl) return

      // 创建容器div
      const container = document.createElement('div')
      container.className = 'pdf-viewer-wrapper'
      container.style.margin = '20px 0'

      mountPdfViewer(container, pdfUrl)

      // 替换占位符
      if (placeholder.parentNode) {
        placeholder.parentNode.replaceChild(container, placeholder)
      }
    })

    // 同时检查是否有PDF链接需要转换为查看器
    const pdfLinks = bodyRef.value.querySelectorAll('a[href$=".pdf"]')
    pdfLinks.forEach((link) => {
      const href = link.getAttribute('href')
      if (href && href.includes('/api/uploads/')) {
        // 检查是否已经有占位符，避免重复
        const existing = link.closest('.pdf-viewer-wrapper')
        if (!existing) {
          const container = document.createElement('div')
          container.className = 'pdf-viewer-wrapper'
          container.style.margin = '20px 0'

          mountPdfViewer(container, href)

          if (link.parentNode) {
            link.parentNode.replaceChild(container, link)
          }
        }
      }
    })
  }

  return {
    renderMathFormulas,
    replacePdfPlaceholders,
    cleanupPdfViewers
  }
}
