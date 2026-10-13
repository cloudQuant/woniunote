import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { installLocalStorage, silenceExpectedConsole } from '@/test/harness'

installLocalStorage()
silenceExpectedConsole(['log', 'warn', 'error'])

const m = vi.hoisted(() => ({ apps: [], logInfo: vi.fn() }))

// createApp 打桩：只记录 use/mount/unmount，避免真实挂载 PdfViewer（pdfjs-dist）。
vi.mock('vue', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    createApp: vi.fn(() => {
      const app = { use: vi.fn(), mount: vi.fn(), unmount: vi.fn() }
      m.apps.push(app)
      return app
    })
  }
})
vi.mock('@/components/viewer/PdfViewer.vue', () => ({
  default: { name: 'PdfViewer', render: () => null }
}))
vi.mock('@/utils/logger', () => ({ logInfo: m.logInfo }))

import { useArticleRendering } from './useArticleRendering'

function setup() {
  const bodyRef = ref(null)
  return { bodyRef, api: useArticleRendering(bodyRef) }
}

/** 创建一段挂在 document 上的正文容器（replaceChild 需要真实父节点）。 */
function makeBody(html = '') {
  const el = document.createElement('div')
  el.innerHTML = html
  document.body.appendChild(el)
  return el
}

afterEach(() => {
  delete window.MathJax
  document.body.innerHTML = ''
  vi.useRealTimers()
})

describe('useArticleRendering —— renderMathFormulas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.apps.length = 0
  })

  it('无容器时直接返回，不触发 MathJax', () => {
    vi.useFakeTimers()
    window.MathJax = { typeset: vi.fn() }
    const { api } = setup()
    api.renderMathFormulas()
    vi.advanceTimersByTime(200)
    expect(window.MathJax.typeset).not.toHaveBeenCalled()
  })

  it('MathJax 3.x：延迟后调用 typeset 并记录日志', () => {
    vi.useFakeTimers()
    window.MathJax = { typeset: vi.fn() }
    const { bodyRef, api } = setup()
    const el = makeBody('<p>$$x^2$$</p>')
    bodyRef.value = el

    api.renderMathFormulas()
    expect(window.MathJax.typeset).not.toHaveBeenCalled() // 延迟执行确保 DOM 已更新
    vi.advanceTimersByTime(100)

    expect(window.MathJax.typeset).toHaveBeenCalledWith([el])
    expect(m.logInfo).toHaveBeenCalledWith('MathJax公式渲染成功')
  })

  it('MathJax 2.x：回退到 Hub.Queue', () => {
    vi.useFakeTimers()
    const hub = { Queue: vi.fn() }
    window.MathJax = { Hub: hub }
    const { bodyRef, api } = setup()
    const el = makeBody('<p>$$y$$</p>')
    bodyRef.value = el

    api.renderMathFormulas()
    vi.advanceTimersByTime(100)

    expect(hub.Queue).toHaveBeenCalledWith(['Typeset', hub, el])
  })

  it('MathJax 未加载时静默跳过', () => {
    vi.useFakeTimers()
    delete window.MathJax
    const { bodyRef, api } = setup()
    bodyRef.value = makeBody('<p>$$z$$</p>')

    api.renderMathFormulas()
    vi.advanceTimersByTime(100)

    expect(console.error).not.toHaveBeenCalled()
  })

  it('typeset 抛错时被捕获并打印错误', () => {
    vi.useFakeTimers()
    window.MathJax = {
      typeset: vi.fn(() => {
        throw new Error('mathjax boom')
      })
    }
    const { bodyRef, api } = setup()
    bodyRef.value = makeBody('<p>$$x$$</p>')

    api.renderMathFormulas()
    expect(() => vi.advanceTimersByTime(100)).not.toThrow()
    expect(console.error).toHaveBeenCalledWith('MathJax渲染失败:', expect.any(Error))
  })
})

describe('useArticleRendering —— PDF 占位符替换', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.apps.length = 0
  })

  it('无容器时直接返回，不创建应用实例', () => {
    const { api } = setup()
    api.replacePdfPlaceholders()
    expect(m.apps).toHaveLength(0)
  })

  it('没有占位符时只记录数量，不创建应用实例', () => {
    const { bodyRef, api } = setup()
    bodyRef.value = makeBody('<p>纯文本</p>')
    api.replacePdfPlaceholders()
    expect(m.apps).toHaveLength(0)
    expect(m.logInfo).toHaveBeenCalledWith('Found PDF placeholders', { count: 0 })
  })

  it('单个占位符被替换为挂载了 PdfViewer 的容器', () => {
    const { bodyRef, api } = setup()
    const el = makeBody('<div class="pdf-viewer-placeholder" data-pdf-url="/api/uploads/a.pdf"></div>')
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(1)
    // 不再全量 app.use(ElementPlus)：PdfViewer 用到的 EP 组件由构建期 resolver 按需注入
    expect(m.apps[0].use).not.toHaveBeenCalled()
    expect(m.apps[0].mount).toHaveBeenCalledTimes(1)
    expect(el.querySelector('.pdf-viewer-placeholder')).toBeNull()
    const wrapperEl = el.querySelector('.pdf-viewer-wrapper')
    expect(wrapperEl).not.toBeNull()
    expect(wrapperEl.style.margin).toBe('20px 0px')
  })

  it('多个占位符各创建一个实例，缺少 data-pdf-url 的占位符被跳过', () => {
    const { bodyRef, api } = setup()
    const el = makeBody(
      '<div class="pdf-viewer-placeholder" data-pdf-url="/api/uploads/a.pdf"></div>' +
        '<div class="pdf-viewer-placeholder"></div>' +
        '<div class="pdf-viewer-placeholder" data-pdf-url="/api/uploads/b.pdf"></div>'
    )
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(2)
    expect(el.querySelectorAll('.pdf-viewer-wrapper')).toHaveLength(2)
  })

  it('把指向 /api/uploads/ 的 .pdf 链接转换为查看器', () => {
    const { bodyRef, api } = setup()
    const el = makeBody('<p><a href="/api/uploads/doc.pdf">下载</a></p>')
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(1)
    expect(el.querySelector('a')).toBeNull()
    expect(el.querySelector('.pdf-viewer-wrapper')).not.toBeNull()
  })

  it('带查询串或锚点的 /api/uploads/ PDF 链接同样被转换', () => {
    const { bodyRef, api } = setup()
    const el = makeBody(
      '<p><a href="/api/uploads/doc.pdf?v=2">下载A</a><a href="/api/uploads/other.pdf#page=2">下载B</a></p>'
    )
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(2)
    expect(el.querySelectorAll('a')).toHaveLength(0)
    expect(el.querySelectorAll('.pdf-viewer-wrapper')).toHaveLength(2)
  })

  it('非 .pdf 结尾的 /api/uploads/ 链接保持原样', () => {
    const { bodyRef, api } = setup()
    const el = makeBody('<p><a href="/api/uploads/notes.txt?v=1">文本</a></p>')
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(0)
    expect(el.querySelector('a')).not.toBeNull()
  })

  it('非 /api/uploads/ 的 .pdf 链接保持原样', () => {
    const { bodyRef, api } = setup()
    const el = makeBody('<p><a href="/static/files/doc.pdf">下载</a></p>')
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(0)
    expect(el.querySelector('a').getAttribute('href')).toBe('/static/files/doc.pdf')
  })

  it('已在 pdf-viewer-wrapper 内的链接不重复挂载', () => {
    const { bodyRef, api } = setup()
    const el = makeBody(
      '<div class="pdf-viewer-wrapper"><a href="/api/uploads/doc.pdf">下载</a></div>'
    )
    bodyRef.value = el

    api.replacePdfPlaceholders()

    expect(m.apps).toHaveLength(0)
    expect(el.querySelectorAll('.pdf-viewer-wrapper')).toHaveLength(1)
  })

  it('再次替换前先卸载上一次创建的实例', () => {
    const { bodyRef, api } = setup()
    const el = makeBody(
      '<div class="pdf-viewer-placeholder" data-pdf-url="/api/uploads/a.pdf"></div>'
    )
    bodyRef.value = el

    api.replacePdfPlaceholders()
    const firstApp = m.apps[0]

    // 模拟正文重新渲染后再次出现占位符
    el.innerHTML =
      '<div class="pdf-viewer-placeholder" data-pdf-url="/api/uploads/b.pdf"></div>'
    api.replacePdfPlaceholders()

    expect(firstApp.unmount).toHaveBeenCalledTimes(1)
    expect(m.apps).toHaveLength(2)
  })
})

describe('useArticleRendering —— cleanupPdfViewers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.apps.length = 0
  })

  it('卸载全部实例并清空记录，重复调用不再卸载', () => {
    const { bodyRef, api } = setup()
    bodyRef.value = makeBody(
      '<div class="pdf-viewer-placeholder" data-pdf-url="/a.pdf"></div>' +
        '<div class="pdf-viewer-placeholder" data-pdf-url="/b.pdf"></div>'
    )
    api.replacePdfPlaceholders()
    expect(m.apps).toHaveLength(2)

    api.cleanupPdfViewers()
    expect(m.apps[0].unmount).toHaveBeenCalledTimes(1)
    expect(m.apps[1].unmount).toHaveBeenCalledTimes(1)

    api.cleanupPdfViewers()
    expect(m.apps[0].unmount).toHaveBeenCalledTimes(1)
    expect(m.apps[1].unmount).toHaveBeenCalledTimes(1)
  })

  it('实例已卸载导致 unmount 抛错时被忽略', () => {
    const { bodyRef, api } = setup()
    bodyRef.value = makeBody(
      '<div class="pdf-viewer-placeholder" data-pdf-url="/a.pdf"></div>'
    )
    api.replacePdfPlaceholders()
    m.apps[0].unmount.mockImplementation(() => {
      throw new Error('already unmounted')
    })

    expect(() => api.cleanupPdfViewers()).not.toThrow()
  })
})
