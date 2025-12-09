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
      
      // 监听内容变化
      editor.addListener('contentChange', () => {
        const content = editor.getContent()
        emit('update:modelValue', content)
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
  border: 1px solid #dcdfe6 !important;
  border-radius: 4px;
}

:deep(.edui-editor-toolbarbox) {
  border-bottom: 1px solid #dcdfe6 !important;
  background: #f5f7fa !important;
}

:deep(.edui-editor-iframeholder) {
  border: none !important;
}
</style>
