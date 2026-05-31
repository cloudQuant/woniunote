import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import fc from 'fast-check'

import { installLocalStorage, mountOptions } from '@/test/harness'
import { contrastRatio, hexToRgb } from '@/utils/contrast'

installLocalStorage()

// ArticleCard uses useRouter() at setup; provide a stub so mounting works.
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

// Mock the article store so importing ArticleCard.vue does not pull in @/api
// (axios/router/element-plus). getTypeName drives the placeholder label.
vi.mock('@/stores/article', () => ({
  useArticleStore: () => ({ getTypeName: (t) => (t ? `分类-${t}` : '') })
}))

// useThemeStore is intentionally NOT mocked: the recompute test drives the real
// theme store via setTheme() to prove the thumbnailUrl computed re-evaluates.
import { useThemeStore } from '@/stores/theme'
import ArticleCard, { buildPlaceholderSvg } from './ArticleCard.vue'

const DATA_URI_PREFIX = 'data:image/svg+xml,'
const READABLE_CONTRAST_MIN = 4.5

// 旧硬编码 Element 调色板（R12 要求占位图取色不得再来自这些固定色值）。
const OLD_ELEMENT_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#6f7ad3']

// 受控令牌桩：让测试掌控调色板来源，从而断言「背景取自传入令牌」而非旧色板。
const STUB_TOKENS = {
  '--wn-color-primary': '#3366cc',
  '--wn-color-on-primary': '#ffffff',
  '--wn-color-surface-2': '#f0f0f0',
  '--wn-color-border': '#cccccc'
}
const stubReadToken = (name) => STUB_TOKENS[name] || ''

/* -------------------------------------------------------------------------- */
/* 调色板重建：与 ArticleCard.vue 内 buildPlaceholderPalette 同构，用于在测试中   */
/* 校验「选用背景取自令牌派生调色板」与「取色索引界内」。                          */
/* -------------------------------------------------------------------------- */
function rgbToHex(r, g, b) {
  const to2 = (n) => {
    const v = Math.max(0, Math.min(255, Math.round(n)))
    return v.toString(16).padStart(2, '0')
  }
  return `#${to2(r)}${to2(g)}${to2(b)}`
}
function normalizeHex(value) {
  const rgb = hexToRgb(value)
  if (!rgb) return null
  return rgbToHex(rgb[0], rgb[1], rgb[2])
}
function mixHex(hexA, hexB, weightA) {
  const a = hexToRgb(hexA)
  const b = hexToRgb(hexB)
  if (!a || !b) return null
  const w = Math.max(0, Math.min(1, weightA))
  return rgbToHex(
    a[0] * w + b[0] * (1 - w),
    a[1] * w + b[1] * (1 - w),
    a[2] * w + b[2] * (1 - w)
  )
}
function pickReadableText(bg, preferred) {
  if (preferred) {
    const p = normalizeHex(preferred)
    if (p && contrastRatio(p, bg) >= READABLE_CONTRAST_MIN) return p
  }
  return contrastRatio('#ffffff', bg) >= contrastRatio('#000000', bg) ? '#ffffff' : '#000000'
}
function buildExpectedPalette(read) {
  const primary = normalizeHex(read('--wn-color-primary')) || '#cc785c'
  const onPrimary = normalizeHex(read('--wn-color-on-primary')) || '#ffffff'
  const surface2 =
    normalizeHex(read('--wn-color-surface-2')) ||
    normalizeHex(read('--wn-color-surface-soft')) ||
    primary
  const border = normalizeHex(read('--wn-color-border')) || surface2
  const palette = [{ bg: primary, text: pickReadableText(primary, onPrimary) }]
  const derived = [
    mixHex(primary, surface2, 0.72),
    mixHex(primary, surface2, 0.5),
    mixHex(primary, border, 0.62)
  ]
  for (const bg of derived) {
    if (bg) palette.push({ bg, text: pickReadableText(bg) })
  }
  return palette
}

/** 解码 data URI 载荷为 SVG 源串。 */
function decodeSvg(url) {
  return decodeURIComponent(url.slice(DATA_URI_PREFIX.length))
}

describe('ArticleCard buildPlaceholderSvg —— 占位图属性测试', () => {
  // Feature: ui-polish-refinement, Property 3: For any 文章 id（非负整数）与任意分类文案 typeName，给定一组从令牌读取的调色板，buildPlaceholderSvg 的输出满足：(a) 以 data:image/svg+xml, 开头且为合法可解码字符串；(b) 选用的背景色取自传入的令牌调色板（不含任何硬编码的旧 Element 色值）；(c) 取色索引落在 [0, palette.length) 内；(d) 解码后的 SVG 包含 typeName 文本；(e) 文字色与所选背景色的对比度达到可读阈值（≥ 4.5）。
  it('占位图取色源自传入令牌调色板、索引界内、含分类文案且文字对比 ≥ 4.5', () => {
    const palette = buildExpectedPalette(stubReadToken)
    const paletteBgs = palette.map((e) => e.bg.toLowerCase())

    fc.assert(
      fc.property(fc.nat(), fc.string(), (articleid, typeName) => {
        const url = buildPlaceholderSvg({ articleid, typeName, readToken: stubReadToken })

        // (a) 以 data URI 前缀开头且可被 decodeURIComponent 合法解码
        expect(url.startsWith(DATA_URI_PREFIX)).toBe(true)
        const decoded = decodeSvg(url)
        expect(decoded.startsWith('<svg')).toBe(true)

        // (d) 解码后 SVG 含分类文案（空/缺省 typeName 由函数回退为 '文章'）
        const label = typeName == null || typeName === '' ? '文章' : String(typeName)
        expect(decoded.includes(label)).toBe(true)

        // 提取背景矩形与文字的填充色
        const bgMatch = decoded.match(/<rect fill="([^"]+)"/)
        const textMatch = decoded.match(/<text[^>]*fill="([^"]+)"/)
        expect(bgMatch).not.toBeNull()
        expect(textMatch).not.toBeNull()
        const bg = bgMatch[1].toLowerCase()
        const text = textMatch[1]

        // (c) 取色索引落在 [0, palette.length)
        const index = Math.abs(Math.trunc(articleid)) % palette.length
        expect(index).toBeGreaterThanOrEqual(0)
        expect(index).toBeLessThan(palette.length)

        // (b) 背景取自令牌派生调色板（且恰为索引对应项），不含旧 Element 色值
        expect(paletteBgs).toContain(bg)
        expect(bg).toBe(palette[index].bg.toLowerCase())
        expect(OLD_ELEMENT_COLORS).not.toContain(bg)

        // (e) 文字/背景对比度达到可读阈值
        expect(contrastRatio(text, bg)).toBeGreaterThanOrEqual(READABLE_CONTRAST_MIN)
      }),
      { numRuns: 100 }
    )
  })
})

describe('ArticleCard.vue —— 缩略图三级回退与主题响应式', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.documentElement.style.removeProperty('--wn-color-primary')
  })

  it('thumbnail 为相对文件名时走后端缩略图路由（非 SVG 占位）', () => {
    const wrapper = mount(
      ArticleCard,
      mountOptions({ props: { article: { articleid: 1, headline: 'h', thumbnail: '101.png' } } })
    )
    const url = wrapper.vm.thumbnailUrl
    expect(url.startsWith('/api/thumb/')).toBe(true)
    expect(url).toContain('101.png')
    expect(url.startsWith(DATA_URI_PREFIX)).toBe(false)
  })

  it('thumbnail 为完整 URL 时原样使用（非 SVG 占位）', () => {
    const full = 'https://cdn.example.com/cover.png'
    const wrapper = mount(
      ArticleCard,
      mountOptions({ props: { article: { articleid: 1, headline: 'h', thumbnail: full } } })
    )
    expect(wrapper.vm.thumbnailUrl).toBe(full)
  })

  it('无 thumbnail 但有 type 时走 /api/thumb/<type>.png（非 SVG 占位）', () => {
    const wrapper = mount(
      ArticleCard,
      mountOptions({ props: { article: { articleid: 1, headline: 'h', type: 101 } } })
    )
    const url = wrapper.vm.thumbnailUrl
    expect(url.startsWith('/api/thumb/')).toBe(true)
    expect(url).toContain('101.png')
    expect(url.startsWith(DATA_URI_PREFIX)).toBe(false)
  })

  it('无 thumbnail 且无 type 时回退到 SVG 占位图', () => {
    const wrapper = mount(
      ArticleCard,
      mountOptions({ props: { article: { articleid: 3, headline: 'h' } } })
    )
    expect(wrapper.vm.thumbnailUrl.startsWith(DATA_URI_PREFIX)).toBe(true)
  })

  it('切换 themeStore.currentTheme 后 SVG 占位图的 thumbnailUrl 重算', async () => {
    // 让 getComputedStyle 在 jsdom 下读到可控的主色令牌。
    document.documentElement.style.setProperty('--wn-color-primary', '#3366cc')
    const wrapper = mount(
      ArticleCard,
      mountOptions({ props: { article: { articleid: 3, headline: 'h' } } })
    )
    const url1 = wrapper.vm.thumbnailUrl
    expect(url1.startsWith(DATA_URI_PREFIX)).toBe(true)

    // 改变令牌取值并切换主题：currentTheme 变化 → computed 重算 → 读到新令牌。
    document.documentElement.style.setProperty('--wn-color-primary', '#cc3366')
    const themeStore = useThemeStore()
    themeStore.setTheme('linear')
    await nextTick()

    const url2 = wrapper.vm.thumbnailUrl
    expect(themeStore.currentTheme).toBe('linear')
    expect(url2.startsWith(DATA_URI_PREFIX)).toBe(true)
    expect(url2).not.toBe(url1)
  })
})
