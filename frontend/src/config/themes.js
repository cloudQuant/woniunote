/**
 * @file themes.js
 * @description 主题清单元数据。
 *
 * 每套主题对应 assets/themes/<key>.css 中的 [data-theme="<key>"] 覆盖规则。
 * swatch 用于切换器九宫格的色板小样预览。
 * dark 决定是否在 <html> 上加 'dark' class（启用 Element Plus 暗色 css-vars 基底）。
 *
 * 新增第 N 套主题流程：
 *   1. 从 awesome-design-md 复制对应 DESIGN.md 的 token；
 *   2. 新建 assets/themes/<key>.css 写 [data-theme="<key>"] 覆盖；
 *   3. 在 assets/themes/index.css 加 @import；
 *   4. 在本文件 THEMES 数组追加一项即可被切换器识别。
 */

/**
 * 默认主题 key（首次访问、无持久化记录时使用）。
 */
export const DEFAULT_THEME = 'claude'

/**
 * localStorage 持久化键名。
 */
export const THEME_STORAGE_KEY = 'wn-theme'

/**
 * 主题清单。
 * @type {Array<{key:string,name:string,desc:string,dark:boolean,swatch:string[],nav:string}>}
 */
export const THEMES = [
  {
    key: 'claude',
    name: 'Claude 暖调',
    desc: '纸感阅读 · 珊瑚强调 · 衬线标题',
    dark: false,
    swatch: ['#fcf8f3', '#ae563d', '#1d1815', '#fffdf9'],
    nav: '#1d1815',
  },
  {
    key: 'notion',
    name: 'Notion 简约',
    desc: '清爽工作区 · 靛紫操作色 · 轻边框',
    dark: false,
    swatch: ['#fdfdfc', '#5046a8', '#191919', '#ffffff'],
    nav: '#191919',
  },
  {
    key: 'vercel',
    name: 'Vercel 黑白',
    desc: '石墨极简 · 高对比 · 克制阴影',
    dark: false,
    swatch: ['#fafafa', '#18181b', '#18181b', '#ffffff'],
    nav: '#18181b',
  },
  {
    key: 'stripe',
    name: 'Stripe 靛蓝',
    desc: '冷调金融 · 靛蓝行动色 · 柔和层级',
    dark: false,
    swatch: ['#f7f8ff', '#5746af', '#17203b', '#ffffff'],
    nav: '#17203b',
  },
  {
    key: 'starbucks',
    name: 'Starbucks 大地绿',
    desc: '森林纸感 · 深绿行动色 · 圆润卡片',
    dark: false,
    swatch: ['#f5f2ec', '#006241', '#18322c', '#fffcf8'],
    nav: '#18322c',
  },
  {
    key: 'linear',
    name: 'Linear 深邃',
    desc: '深空专注 · 薰衣草焦点 · 精密边界',
    dark: true,
    swatch: ['#0d0e12', '#a5b4fc', '#f5f7ff', '#14151b'],
    nav: '#111217',
  },
  {
    key: 'spotify',
    name: 'Spotify 暗夜',
    desc: '音浪暗夜 · 绿色行动色 · 大圆角',
    dark: true,
    swatch: ['#121212', '#1ed760', '#ffffff', '#1a1a1a'],
    nav: '#070707',
  },
  {
    key: 'supabase',
    name: 'Supabase 翡翠',
    desc: '翡翠代码 · 清晰状态色 · 平直层级',
    dark: true,
    swatch: ['#111817', '#3ecf8e', '#f4fffa', '#17211f'],
    nav: '#0c1210',
  },
  {
    key: 'sentry',
    name: 'Sentry 暗紫',
    desc: '暗紫数据 · 高亮链接 · 分层阴影',
    dark: true,
    swatch: ['#180f25', '#a78bfa', '#fbf8ff', '#211633'],
    nav: '#140a20',
  },
]

/**
 * 所有合法主题 key 集合，便于校验。
 */
export const THEME_KEYS = THEMES.map((t) => t.key)

/**
 * 按 key 查主题元数据。
 * @param {string} key
 * @returns {object|undefined}
 */
export function getThemeMeta(key) {
  return THEMES.find((t) => t.key === key)
}
