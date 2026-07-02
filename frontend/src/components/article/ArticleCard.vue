<template>
  <div class="article-item" @click="goToDetail">
    <!-- 左侧缩略图 -->
    <div class="article-thumbnail">
      <img 
        :src="thumbnailUrl" 
        :alt="article.headline"
        @error="handleImageError"
      />
    </div>
    
    <!-- 右侧内容 -->
    <div class="article-content">
      <h3 class="article-title">{{ article.headline }}</h3>
      
      <div class="article-meta">
        <span class="meta-item">作者: {{ article.author?.nickname || '匿名' }}</span>
        <span class="meta-item">类别: {{ typeName }}</span>
        <span class="meta-item">日期: {{ formatDate(article.createtime) }}</span>
        <span class="meta-item">阅读: {{ article.readcount || 0 }}次</span>
        <span class="meta-item">消耗积分: {{ article.credit || 0 }}分</span>
      </div>
      
      <p class="article-excerpt">{{ excerpt }}</p>
    </div>
  </div>
</template>

<script>
/**
 * 占位图工具（纯函数，独立于组件实例，便于单元测试）。
 *
 * SVG 占位图以 data URI 形式作为 <img src>，脱离文档 CSS 级联，无法直接用
 * var(--wn-*)。因此颜色必须在 JS 运行时从当前主题令牌读取后注入字符串。
 * buildPlaceholderSvg 设计为可注入 readToken，使其在 jsdom（无真实主题 CSS）
 * 下也能通过桩函数测试，并在令牌读空时回退到 :root 默认主色，始终产出合法 SVG。
 */
import { contrastRatio, hexToRgb } from '@/utils/contrast'

/** :root 默认主色（tokens.css 的 Claude 暖调兜底；令牌读空时使用，防止空 fill） */
const PLACEHOLDER_FALLBACK_PRIMARY = '#cc785c'
/** :root 默认 on-primary（主色上的文字色兜底） */
const PLACEHOLDER_FALLBACK_ON_PRIMARY = '#ffffff'
/** WCAG AA 正文可读对比度阈值 */
const READABLE_CONTRAST_MIN = 4.5

/**
 * 默认令牌读取器：从文档根的计算样式读取自定义属性。
 * 在 jsdom 或缺失环境下返回空串，由调用方回退到默认色。
 * @param {string} name - CSS 自定义属性名（如 '--wn-color-primary'）
 * @returns {string} 令牌值（去空白）或空串
 */
function defaultReadToken(name) {
  if (typeof window === 'undefined' || typeof document === 'undefined' || !document.documentElement) {
    return ''
  }
  try {
    return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  } catch {
    return ''
  }
}

/**
 * 将 r/g/b（0-255，允许小数，自动夹取/取整）转为 6 位十六进制颜色串。
 * @returns {string} 形如 '#rrggbb'
 */
function rgbToHex(r, g, b) {
  const to2 = (n) => {
    const v = Math.max(0, Math.min(255, Math.round(n)))
    return v.toString(16).padStart(2, '0')
  }
  return `#${to2(r)}${to2(g)}${to2(b)}`
}

/**
 * 将任意可解析的十六进制颜色规范化为 '#rrggbb'；不可解析（空串/rgb()/非法）返回 null。
 * @param {string} value
 * @returns {string|null}
 */
function normalizeHex(value) {
  const rgb = hexToRgb(value)
  if (!rgb) return null
  return rgbToHex(rgb[0], rgb[1], rgb[2])
}

/**
 * 按权重混合两个十六进制颜色（weightA 为第一个颜色的占比 0..1）。
 * @returns {string|null} 混合后的 '#rrggbb'；任一不可解析时返回 null
 */
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

/**
 * 为给定背景色挑选可读的文字色。
 * 优先使用 preferred（如 --wn-color-on-primary），仅当其对比度达标时采用；
 * 否则按背景明度在黑/白之间取对比度更高者（数学上保证 ≥ ~4.58 ≥ 4.5）。
 * @param {string} bg - 背景色 '#rrggbb'
 * @param {string} [preferred] - 优先文字色
 * @returns {string} '#rrggbb'
 */
function pickReadableText(bg, preferred) {
  if (preferred) {
    const p = normalizeHex(preferred)
    if (p && contrastRatio(p, bg) >= READABLE_CONTRAST_MIN) return p
  }
  const white = '#ffffff'
  const black = '#000000'
  return contrastRatio(white, bg) >= contrastRatio(black, bg) ? white : black
}

/**
 * 从主题令牌派生占位图调色板：以主色为首项，再叠加主色与深表面/边框的衍生梯度。
 * 每项的文字色保证与背景达到可读对比度。令牌读空时回退到默认主色。
 * @param {(name: string) => string} read - 令牌读取器
 * @returns {Array<{ bg: string, text: string }>}
 */
function buildPlaceholderPalette(read) {
  const primary = normalizeHex(read('--wn-color-primary')) || PLACEHOLDER_FALLBACK_PRIMARY
  const onPrimary = normalizeHex(read('--wn-color-on-primary')) || PLACEHOLDER_FALLBACK_ON_PRIMARY
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

/**
 * 构建文章缩略图的 SVG 占位图（data URI）。
 *
 * 取色源自当前主题令牌（而非硬编码色板），按 articleid 在调色板中取色，
 * 文字色保证与背景可读对比；令牌读空时回退到 :root 默认主色，始终产出合法 SVG。
 *
 * @param {Object} input
 * @param {number} input.articleid - 文章 id（非负整数；用于稳定取色）
 * @param {string} input.typeName - 分类文案（显示在占位图上）
 * @param {string} [input.theme] - 当前主题 key（仅供调用方建立响应式依赖，函数内不使用）
 * @param {(name: string) => string} [input.readToken] - 令牌读取器（默认读 documentElement 计算样式；测试可注入桩）
 * @returns {string} 形如 "data:image/svg+xml,<encoded>"
 */
export function buildPlaceholderSvg(input = {}) {
  const { articleid, typeName, readToken } = input
  const read = typeof readToken === 'function' ? readToken : defaultReadToken
  const palette = buildPlaceholderPalette(read)
  const id = Number.isFinite(articleid) ? Math.abs(Math.trunc(articleid)) : 0
  const index = id % palette.length
  const { bg, text } = palette[index]
  const label = typeName == null || typeName === '' ? '文章' : String(typeName)
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="130" viewBox="0 0 200 130">' +
    `<rect fill="${bg}" width="200" height="130"/>` +
    `<text x="100" y="65" text-anchor="middle" dominant-baseline="middle" fill="${text}" font-size="20" font-weight="bold" font-family="sans-serif">${label}</text>` +
    '</svg>'
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
</script>

<script setup>
/**
 * @component ArticleCard
 * @description 文章卡片组件
 * 展示文章的缩略图、标题、元数据（作者、分类、日期等）和摘要。
 * 支持缩略图自动回退机制（后端缩略图 -> 类型默认图 -> SVG 占位图）。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useArticleStore } from '@/stores/article'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  /**
   * 文章对象
   * @type {Object}
   */
  article: {
    type: Object,
    required: true
  }
})

const router = useRouter()
const articleStore = useArticleStore()
const themeStore = useThemeStore()

// 缓存破坏版本号（更新缩略图后递增此值）
const THUMB_VERSION = 'v3'

/**
 * 计算缩略图 URL
 * 1. 如果有 thumbnail 字段，使用后端缩略图服务
 * 2. 如果有 type 字段，使用类型默认缩略图
 * 3. 兜底使用 SVG 占位图
 */
const thumbnailUrl = computed(() => {
  // 1. 如果后端返回了具体的 thumbnail 字段，认为是 thumb 文件名，例如 "101.png"
  if (props.article.thumbnail) {
    // 如果已经是完整URL，直接返回
    if (props.article.thumbnail.startsWith('http://') || props.article.thumbnail.startsWith('https://')) {
      return props.article.thumbnail
    }
    // 否则走新后端缩略图路由（带版本号防止缓存）
    return `/api/thumb/${props.article.thumbnail}?${THUMB_VERSION}`
  }

  // 2. 如果没有 thumbnail，但有文章类型，则使用类型ID自动生成缩略图
  if (props.article.type) {
    return `/api/thumb/${props.article.type}.png?${THUMB_VERSION}`
  }

  // 3. 最后兜底：使用 SVG data URL 作为占位图（取色源自当前主题令牌）
  // 显式读取 currentTheme 建立响应式依赖：主题切换 → computed 重算 →
  // getComputedStyle 读到新令牌 → 占位图重渲染（R12.2）。
  const _themeKey = themeStore.currentTheme
  return buildPlaceholderSvg({
    articleid: props.article.articleid || 0,
    typeName: articleStore.getTypeName(props.article.type) || '文章',
    theme: _themeKey
  })
})

/**
 * 获取文章分类名称
 */
const typeName = computed(() => {
  return articleStore.getTypeName(props.article.type) || '未分类'
})

/**
 * 生成文章摘要
 * 移除 HTML 标签并截取前 150 个字符
 */
const excerpt = computed(() => {
  // 从content中提取纯文本摘要
  if (!props.article.content) return ''
  const text = props.article.content
    .replace(/<[^>]+>/g, '')  // 移除HTML标签
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  const MAX_EXCERPT_LENGTH = 80
  return text.length > MAX_EXCERPT_LENGTH ? text.slice(0, MAX_EXCERPT_LENGTH) + '...' : text
})

/**
 * 格式化日期
 * @param {string} dateStr - ISO 日期字符串
 * @returns {string} 格式化后的日期字符串 (YYYY-MM-DD HH:mm:ss)
 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

/**
 * 跳转到文章详情页
 */
function goToDetail() {
  router.push({ name: 'ArticleDetail', params: { id: props.article.articleid } })
}

/**
 * 图片加载失败处理
 * 使用 SVG 占位图替换（取色源自当前主题令牌）
 */
function handleImageError(event) {
  event.target.src = buildPlaceholderSvg({
    articleid: props.article.articleid || 0,
    typeName: articleStore.getTypeName(props.article.type) || '文章',
    theme: themeStore.currentTheme
  })
}
</script>

<style scoped>
/* 与原站 woniunote 一致的文章卡片样式 */
.article-item {
  display: flex;
  gap: var(--wn-space-4);
  padding: var(--wn-space-4);
  background: var(--wn-color-surface);
  border-radius: var(--wn-radius-md);
  margin-bottom: var(--wn-space-4);
  cursor: pointer;
  box-shadow: var(--wn-shadow-sm);
  /* 交互令牌驱动过渡（与 main.css 统一悬停规范一致，R14.3） */
  transition: box-shadow var(--wn-transition-base), transform var(--wn-transition-base);
}

/* 统一悬停反馈（R14）：抬升阴影 + 标准位移量，颜色/阴影消费令牌随主题变化 */
.article-item:hover {
  box-shadow: var(--wn-elevation-hover);
  transform: translateY(var(--wn-hover-lift));
}

.article-thumbnail {
  flex-shrink: 0;
  width: 226px;
  height: 136px;
  overflow: hidden;
  border-radius: var(--wn-radius-sm);
}

.article-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--wn-transition-base);
}

.article-item:hover .article-thumbnail img {
  transform: scale(1.02);
}

.article-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.article-title {
  font-size: var(--wn-font-size-lg);
  font-weight: normal;
  color: var(--wn-color-text);
  margin: 0 0 var(--wn-space-3);
  line-height: var(--wn-line-height-relaxed);
  cursor: pointer;
}

.article-title:hover {
  color: var(--wn-color-primary);
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: var(--wn-space-3);
  font-size: var(--wn-font-size-base);
  color: var(--wn-color-text-muted);
}

.meta-item {
  display: inline-flex;
  align-items: center;
}

.meta-item::after {
  content: '\00a0\00a0\00a0';
}

.meta-item:last-child::after {
  content: '';
}

.article-excerpt {
  margin: 0;
  font-size: var(--wn-font-size-base);
  color: var(--wn-color-text-muted);
  line-height: var(--wn-line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

@media (max-width: 768px) {
  .article-item {
    flex-direction: column;
  }

  /* 单一显示策略：移动端缩略图铺满容器宽度并以固定 banner 高度显示。
     删除了与之矛盾的 display: none，避免尺寸规则成为死代码（R1.1/R1.3）。 */
  .article-thumbnail {
    width: 100%;
    height: 180px;
  }

  .article-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .article-meta {
    flex-wrap: wrap;
    gap: var(--wn-space-2);
  }

  .meta-item::after {
    content: '';
  }
}

/* 减弱动效偏好（R9.2 / R14.4）：scoped 样式特异度高于全局，需就近覆盖。
   取消卡片悬停位移与缩略图缩放，保留颜色/阴影等非运动类反馈。 */
@media (prefers-reduced-motion: reduce) {
  .article-item:hover {
    transform: none;
  }

  .article-item:hover .article-thumbnail img {
    transform: none;
  }
}
</style>
