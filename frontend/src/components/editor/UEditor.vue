<template>
  <div class="ueditor-container">
    <div :id="editorId"></div>
  </div>
</template>

<script setup>
/**
 * @component UEditor
 * @description 百度 UEditor 富文本编辑器组件封装
 * 支持 v-model 双向绑定、自定义配置、动态加载脚本以及 PDF 上传处理。
 */
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  /**
   * 编辑器内容 (v-model)
   */
  modelValue: {
    type: String,
    default: ''
  },
  /**
   * UEditor 配置对象
   * 会与默认配置合并
   */
  config: {
    type: Object,
    default: () => ({})
  },
  /**
   * 编辑器容器 ID
   * 默认为随机生成的唯一 ID
   */
  editorId: {
    type: String,
    default: () => `editor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
})

const emit = defineEmits([
  /**
   * 内容更新事件
   * @arg {string} content - 新的 HTML 内容
   */
  'update:modelValue', 
  /**
   * 编辑器就绪事件
   * @arg {Object} editor - UEditor 实例
   */
  'ready'
])

let editor = null
const isReady = ref(false)
const themeStore = useThemeStore()

/**
 * 把当前主题令牌注入编辑器 iframe 的内部文档。
 * UEditor 的编辑区是一个同源 iframe，父页面 CSS 无法穿透，
 * 需要直接往其 document.head 注入 <style>，并在主题切换时刷新。
 * 颜色值从父页面计算样式读取（已由 [data-theme] 决定），保证与全站一致。
 */
function applyEditorTheme() {
  if (!editor) return
  // UEditor 提供 editor.document（编辑区 iframe 的 document）
  const doc = editor.document
  if (!doc || !doc.head) return

  // 从父页面读取当前主题的实际令牌值
  const root = getComputedStyle(document.documentElement)
  const v = (name, fallback) => (root.getPropertyValue(name) || fallback).trim()
  const bg = v('--wn-color-surface', '#ffffff')
  const text = v('--wn-color-text', '#333333')
  const link = v('--wn-color-link', '#409eff')
  const border = v('--wn-color-border', '#e6dfd8')
  const codeBg = v('--wn-color-surface-soft', '#f5f5f5')
  const muted = v('--wn-color-text-muted', '#909399')

  const css = `
    html, body { background: ${bg} !important; color: ${text} !important; }
    body { caret-color: ${text}; }
    a { color: ${link} !important; }
    p, span, div, li, td, th, h1, h2, h3, h4, h5, h6 { color: ${text}; }
    blockquote { color: ${muted}; border-left: 3px solid ${border}; }
    pre, code { background: ${codeBg} !important; color: ${text} !important; }
    table, th, td { border-color: ${border} !important; }
    hr { border-color: ${border}; }
    img { background: transparent; }
  `

  let styleEl = doc.getElementById('wn-editor-theme')
  if (!styleEl) {
    styleEl = doc.createElement('style')
    styleEl.id = 'wn-editor-theme'
    doc.head.appendChild(styleEl)
  }
  styleEl.textContent = css

  // 同步 iframe 外层占位/工具栏区域的底色，避免编辑区与边框间露出白边
  try {
    const iframe = editor.iframe
    if (iframe) iframe.style.background = bg
  } catch (e) { /* 忽略 */ }
}

// 默认配置
const defaultConfig = {
  initialFrameWidth: '100%',
  initialFrameHeight: 400,
  autoHeightEnabled: true,
  autoFloatEnabled: false,
  zIndex: 1000,
  UEDITOR_HOME_URL: '/ueditor/'
}

/**
 * 动态加载脚本
 * @param {string} src - 脚本 URL
 * @returns {Promise<void>}
 */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    // 检查是否已加载
    const existingScript = document.querySelector(`script[src="${src}"]`)
    if (existingScript) {
      resolve()
      return
    }
    
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

/**
 * 初始化编辑器
 * 加载脚本 -> 创建实例 -> 绑定事件
 */
async function initEditor() {
  try {
    // 设置 UEditor 根路径
    window.UEDITOR_HOME_URL = '/ueditor/'
    
    // 加载 UEditor 脚本
    if (!window.UE) {
      await loadScript('/ueditor/ueditor.config.js')
      await loadScript('/ueditor/ueditor.all.js')
    }
    
    // 等待 DOM 更新
    await nextTick()
    
    // 合并配置
    const config = { ...defaultConfig, ...props.config }
    
    // 创建编辑器实例
    editor = window.UE.getEditor(props.editorId, config)
    
    // 编辑器就绪
    editor.ready(() => {
      isReady.value = true
      
      // 设置初始内容
      if (props.modelValue) {
        editor.setContent(props.modelValue)
      }

      // 注入当前主题到编辑区 iframe
      applyEditorTheme()
      
      // 监听内容变化
      editor.addListener('contentChange', () => {
        const content = editor.getContent()
        emit('update:modelValue', content)
        // 某些操作（切换源码模式/setContent）可能重建 iframe 文档，
        // 导致注入的样式丢失；若丢失则补回，保证暗色主题持续生效。
        try {
          if (editor.document && !editor.document.getElementById('wn-editor-theme')) {
            applyEditorTheme()
          }
        } catch (e) { /* 忽略 */ }
      })
      
      // 监听UEditor的文件上传成功事件
      // UEditor上传文件成功后，如果后端返回了html字段，会使用该HTML插入编辑器
      // 否则会插入默认的文件链接
      // 我们通过监听afterUpfile事件来替换默认插入的文件链接为PDF占位符
      editor.addListener('afterUpfile', (type, result) => {
        try {
          // result是后端返回的JSON对象
          if (result && result.fileType === 'pdf' && result.html) {
            // 如果后端返回了html字段，UEditor应该已经插入了
            // 但为了确保，我们检查一下并替换可能的默认链接
            setTimeout(() => {
              const content = editor.getContent()
              const pdfUrl = result.pdfUrl || result.url
              // 查找可能的文件链接并替换为PDF占位符
              const linkPattern = new RegExp(`<a[^>]*href=["']${pdfUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^>]*>.*?</a>`, 'gi')
              if (linkPattern.test(content)) {
                const newContent = content.replace(linkPattern, result.html)
                editor.setContent(newContent)
              }
            }, 200)
          }
        } catch (e) {
          console.warn('处理PDF上传结果失败:', e)
        }
      })
      
      emit('ready', editor)
    })
    
  } catch (error) {
    console.error('Failed to initialize UEditor:', error)
  }
}

// 监听 modelValue 变化，同步到编辑器
watch(() => props.modelValue, (newVal) => {
  if (isReady.value && editor) {
    const currentContent = editor.getContent()
    if (newVal !== currentContent) {
      editor.setContent(newVal || '')
    }
  }
})

// 监听主题切换，刷新编辑区 iframe 内部样式
watch(() => themeStore.currentTheme, () => {
  if (isReady.value) {
    applyEditorTheme()
  }
})

onMounted(() => {
  initEditor()
})

onBeforeUnmount(() => {
  if (editor) {
    try {
      editor.destroy()
    } catch (e) {
      console.warn('Error destroying editor:', e)
    }
    editor = null
  }
})

// 暴露方法供父组件调用
defineExpose({
  /** 获取编辑器实例 */
  getEditor: () => editor,
  /** 获取内容 */
  getContent: () => editor?.getContent() || '',
  /** 设置内容 */
  setContent: (content) => editor?.setContent(content || ''),
  /** 插入 HTML */
  insertHtml: (html) => editor?.execCommand('insertHtml', html),
  /** 聚焦编辑器 */
  focus: () => editor?.focus()
})
</script>

<style scoped>
.ueditor-container {
  width: 100%;
  line-height: normal;
}

/* 覆盖 UEditor 默认样式 */
:deep(.edui-editor) {
  border: 1px solid var(--wn-color-border) !important;
  border-radius: var(--wn-radius-sm);
  background: var(--wn-color-surface) !important;
}

:deep(.edui-editor-toolbarbox) {
  border-bottom: 1px solid var(--wn-color-border) !important;
  background: var(--wn-color-surface-soft) !important;
}

:deep(.edui-editor-toolbarboxouter) {
  background: var(--wn-color-surface-soft) !important;
  border-bottom: 1px solid var(--wn-color-border) !important;
}

:deep(.edui-editor-iframeholder) {
  border: none !important;
  background: var(--wn-color-surface) !important;
}

/* 工具栏按钮在暗色主题下的可读性 */
:deep(.edui-default .edui-toolbar .edui-button .edui-icon),
:deep(.edui-default .edui-toolbar .edui-combox .edui-icon) {
  /* 暗色主题下反色显示单色图标，浅色主题保持原样 */
  filter: var(--wn-editor-icon-filter, none);
}

:deep(.edui-default .edui-toolbar .edui-button-body:hover),
:deep(.edui-default .edui-toolbar .edui-combox-body:hover) {
  background: var(--wn-color-surface-2) !important;
}

:deep(.edui-default .edui-combox-body .edui-button-label) {
  color: var(--wn-color-text) !important;
}

/* 编辑器底部状态栏 */
:deep(.edui-editor-bottombar) {
  background: var(--wn-color-surface-soft) !important;
  border-top: 1px solid var(--wn-color-border) !important;
}
</style>
