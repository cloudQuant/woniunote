/**
 * @file theme.js
 * @description 主题状态管理（Pinia）。
 *
 * 负责：当前主题状态、切换、持久化（localStorage）、把主题应用到 <html>。
 * 应用方式：在 <html> 上设置 data-theme="<key>"，并按 dark 标记切换 'dark' class。
 * CSS 变量（--wn-* / --el-*）级联即时生效，无需重渲染组件。
 */

import { defineStore } from 'pinia'
import {
  THEMES,
  THEME_KEYS,
  DEFAULT_THEME,
  THEME_STORAGE_KEY,
  getThemeMeta,
} from '@/config/themes'

/**
 * 把主题应用到 document（设置 data-theme 与 dark class）。
 * 抽成纯函数，便于 index.html 的防闪烁脚本与 store 复用同一套逻辑。
 * @param {string} key - 主题 key
 */
export function applyThemeToDom(key) {
  const meta = getThemeMeta(key)
  if (!meta || typeof document === 'undefined') return
  const html = document.documentElement
  html.setAttribute('data-theme', key)
  html.classList.toggle('dark', !!meta.dark)
}

/**
 * 读取持久化主题；非法或缺失时回退默认。
 * 首次访问可按系统 prefers-color-scheme 选一个合适的明/暗默认。
 * @returns {string}
 */
function resolveInitialTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved && THEME_KEYS.includes(saved)) return saved
  } catch (e) {
    // localStorage 不可用（隐私模式等），忽略
  }
  // 首次访问：跟随系统明暗偏好挑默认
  try {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'linear' // 暗色默认
    }
  } catch (e) {
    // 忽略
  }
  return DEFAULT_THEME
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    /** @type {string} 当前主题 key */
    currentTheme: DEFAULT_THEME,
    /** @type {Array} 可选主题清单（供 UI 渲染） */
    themes: THEMES,
  }),

  getters: {
    /** 当前主题元数据 */
    currentMeta: (state) => getThemeMeta(state.currentTheme),
    /** 当前是否暗色 */
    isDark: (state) => !!getThemeMeta(state.currentTheme)?.dark,
  },

  actions: {
    /**
     * 初始化主题：从持久化/系统偏好解析并应用。
     * 在 app 挂载前调用（main.js）。
     */
    initTheme() {
      const key = resolveInitialTheme()
      this.currentTheme = key
      applyThemeToDom(key)
    },

    /**
     * 切换到指定主题并持久化。
     * @param {string} key - 主题 key
     */
    setTheme(key) {
      if (!THEME_KEYS.includes(key)) return
      this.currentTheme = key
      applyThemeToDom(key)
      try {
        localStorage.setItem(THEME_STORAGE_KEY, key)
      } catch (e) {
        // localStorage 不可用，忽略
      }
    },
  },
})
