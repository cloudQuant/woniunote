import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import fc from 'fast-check'

import { THEME_KEYS } from '@/config/themes'
import { parseThemeTokens, contrastRatio } from '@/utils/contrast'

/**
 * themeContrast.spec.js —— 9 套主题正文/次级文本对比度（WCAG AA）属性测试。
 *
 * 解析 themes/<key>.css 提取 --wn-color-text / surface / canvas / text-muted，
 * 用 contrast.js 计算对比度，断言：
 *   - text / surface ≥ 4.5（R10.1 正文）
 *   - text / canvas  ≥ 4.5（R10.1 正文）
 *   - text-muted / surface ≥ 3.0（R10.3 次级文本）
 *
 * 单一数据源：直接解析主题 CSS 令牌值，杜绝「改 CSS 忘改测试」的漂移。
 */

// 读取主题 CSS 源文本。vitest 以 frontend/ 为 cwd，按工程相对路径解析，
// 避免 jsdom 下 import.meta.url 非 file scheme 与 `?raw` 在 css:false 时返回空串的问题。
function readThemeColors(themeKey) {
  const cssPath = path.resolve(process.cwd(), `src/assets/themes/${themeKey}.css`)
  const cssText = readFileSync(cssPath, 'utf-8')
  const tokens = parseThemeTokens(cssText)
  return {
    text: tokens['--wn-color-text'],
    surface: tokens['--wn-color-surface'],
    canvas: tokens['--wn-color-canvas'],
    textMuted: tokens['--wn-color-text-muted']
  }
}

// 模块加载时一次性读取全部 9 套主题色值，构建 {themeKey -> {text, surface, canvas, textMuted}}。
const THEME_COLORS = THEME_KEYS.reduce((acc, key) => {
  acc[key] = readThemeColors(key)
  return acc
}, {})

describe('9 套主题正文/次级文本对比度（WCAG AA）', () => {
  // Feature: ui-polish-refinement, Property 2: For any 主题 t ∈ {claude, notion, vercel, stripe, starbucks, linear, spotify, supabase, sentry}：contrastRatio(text(t), surface(t)) ≥ 4.5 且 contrastRatio(text(t), canvas(t)) ≥ 4.5，且 contrastRatio(textMuted(t), surface(t)) ≥ 3.0，其中各色值由解析对应主题 CSS 的 --wn-color-* 令牌得到。
  it('每套主题 text/surface≥4.5、text/canvas≥4.5、muted/surface≥3.0', () => {
    fc.assert(
      fc.property(fc.constantFrom(...THEME_KEYS), (themeKey) => {
        const { text, surface, canvas, textMuted } = THEME_COLORS[themeKey]

        const textSurface = contrastRatio(text, surface)
        const textCanvas = contrastRatio(text, canvas)
        const mutedSurface = contrastRatio(textMuted, surface)

        expect(
          textSurface,
          `theme ${themeKey} text/surface contrast = ${textSurface} (text=${text}, surface=${surface})`
        ).toBeGreaterThanOrEqual(4.5)
        expect(
          textCanvas,
          `theme ${themeKey} text/canvas contrast = ${textCanvas} (text=${text}, canvas=${canvas})`
        ).toBeGreaterThanOrEqual(4.5)
        expect(
          mutedSurface,
          `theme ${themeKey} muted/surface contrast = ${mutedSurface} (textMuted=${textMuted}, surface=${surface})`
        ).toBeGreaterThanOrEqual(3.0)
      }),
      { numRuns: 100 }
    )
  })
})
