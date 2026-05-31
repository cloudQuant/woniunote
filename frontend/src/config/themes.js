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
 * @type {Array<{key:string,name:string,desc:string,dark:boolean,swatch:string[]}>}
 */
export const THEMES = [
  {
    key: 'claude',
    name: 'Claude 暖调',
    desc: '奶油画布 · 珊瑚 · 衬线',
    dark: false,
    swatch: ['#faf9f5', '#cc785c', '#141413', '#efe9de'],
  },
  {
    key: 'notion',
    name: 'Notion 简约',
    desc: '纯白 · 紫色 · 工作区',
    dark: false,
    swatch: ['#ffffff', '#5645d4', '#0a1530', '#f6f5f4'],
  },
  {
    key: 'vercel',
    name: 'Vercel 黑白',
    desc: '极简 · 单色 · 几何',
    dark: false,
    swatch: ['#ffffff', '#171717', '#0070f3', '#fafafa'],
  },
  {
    key: 'stripe',
    name: 'Stripe 靛蓝',
    desc: '冷调 · 靛蓝 · 金融科技',
    dark: false,
    swatch: ['#f6f9fc', '#533afd', '#0d253d', '#e3e8ee'],
  },
  {
    key: 'starbucks',
    name: 'Starbucks 大地绿',
    desc: '暖奶油 · 品牌绿 · 零售',
    dark: false,
    swatch: ['#f2f0eb', '#00754a', '#1e3932', '#edebe9'],
  },
  {
    key: 'linear',
    name: 'Linear 深邃',
    desc: '近黑 · 薰衣草蓝 · 技术',
    dark: true,
    swatch: ['#010102', '#5e6ad2', '#f7f8f8', '#18191a'],
  },
  {
    key: 'spotify',
    name: 'Spotify 暗夜',
    desc: '近黑 · 绿 · 沉浸',
    dark: true,
    swatch: ['#121212', '#1ed760', '#ffffff', '#181818'],
  },
  {
    key: 'supabase',
    name: 'Supabase 翡翠',
    desc: '暗色 · 翡翠绿 · 代码',
    dark: true,
    swatch: ['#1c1c1c', '#3ecf8e', '#ffffff', '#202020'],
  },
  {
    key: 'sentry',
    name: 'Sentry 暗紫',
    desc: '深紫 · 柠檬 · 数据',
    dark: true,
    swatch: ['#1d1127', '#7553ff', '#c2ef4e', '#1f1633'],
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
