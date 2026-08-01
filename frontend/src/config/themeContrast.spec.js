import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import fc from 'fast-check'

import { THEME_KEYS } from '@/config/themes'
import { hexToRgb, parseThemeTokens, contrastRatio } from '@/utils/contrast'

/**
 * themeContrast.spec.js —— 9 套主题的文本、操作与焦点对比度属性测试。
 *
 * 解析 themes/<key>.css 提取 --wn-* 语义令牌，用 contrast.js 计算对比度，断言：
 *   - 正文、次级/弱化文本、链接 / surface ≥ 4.5（普通文本 AA）
 *   - primary 的默认、hover、active 状态 / on-primary ≥ 4.5
 *   - success / warning / error / info 按钮 / 对应 on-* ≥ 4.5
 *   - keyboard focus / surface ≥ 3.0（非文本可见焦点）
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
    textSecondary: tokens['--wn-color-text-secondary'],
    surface: tokens['--wn-color-surface'],
    canvas: tokens['--wn-color-canvas'],
    textMuted: tokens['--wn-color-text-muted'],
    link: tokens['--wn-color-link'],
    primary: tokens['--wn-color-primary'],
    primaryHover: tokens['--wn-color-primary-hover'],
    primaryActive: tokens['--wn-color-primary-active'],
    onPrimary: tokens['--wn-color-on-primary'],
    success: tokens['--wn-color-success'],
    onSuccess: tokens['--wn-color-on-success'],
    warning: tokens['--wn-color-warning'],
    onWarning: tokens['--wn-color-on-warning'],
    error: tokens['--wn-color-error'],
    onError: tokens['--wn-color-on-error'],
    info: tokens['--wn-color-info'],
    onInfo: tokens['--wn-color-on-info'],
    focus: tokens['--wn-color-focus']
  }
}

/**
 * Match the opaque `color-mix(in srgb, foreground P%, background)` use in
 * tokens.css closely enough to verify contrast before browser rendering.
 */
function mixSrgb(foreground, background, foregroundWeight) {
  const foregroundRgb = hexToRgb(foreground)
  const backgroundRgb = hexToRgb(background)
  const backgroundWeight = 1 - foregroundWeight

  return `#${foregroundRgb
    .map((channel, index) => Math.round(channel * foregroundWeight + backgroundRgb[index] * backgroundWeight)
      .toString(16)
      .padStart(2, '0'))
    .join('')}`
}

// 模块加载时一次性读取全部 9 套主题色值，构建 {themeKey -> {text, surface, canvas, textMuted}}。
const THEME_COLORS = THEME_KEYS.reduce((acc, key) => {
  acc[key] = readThemeColors(key)
  return acc
}, {})

describe('9 套主题可访问令牌对比度', () => {
  // Feature: theme-system-refresh, Property 1: For any configured theme, all normal text,
  // link and filled-action foreground/background pairs meet WCAG AA (4.5:1), while the
  // visible keyboard focus color meets the non-text 3:1 threshold against its surface.
  it('每套主题的文本、链接、按钮各状态和焦点均满足令牌契约', () => {
    fc.assert(
      fc.property(fc.constantFrom(...THEME_KEYS), (themeKey) => {
        const colors = THEME_COLORS[themeKey]
        const {
          text,
          textSecondary,
          surface,
          canvas,
          textMuted,
          link,
          primary,
          primaryHover,
          primaryActive,
          onPrimary,
          success,
          onSuccess,
          warning,
          onWarning,
          error,
          onError,
          info,
          onInfo,
          focus
        } = colors

        const textSurface = contrastRatio(text, surface)
        const textCanvas = contrastRatio(text, canvas)
        const secondarySurface = contrastRatio(textSecondary, surface)
        const mutedSurface = contrastRatio(textMuted, surface)
        const linkSurface = contrastRatio(link, surface)

        expect(
          textSurface,
          `theme ${themeKey} text/surface contrast = ${textSurface} (text=${text}, surface=${surface})`
        ).toBeGreaterThanOrEqual(4.5)
        expect(
          textCanvas,
          `theme ${themeKey} text/canvas contrast = ${textCanvas} (text=${text}, canvas=${canvas})`
        ).toBeGreaterThanOrEqual(4.5)
        expect(
          secondarySurface,
          `theme ${themeKey} secondary/surface contrast = ${secondarySurface}`
        ).toBeGreaterThanOrEqual(4.5)
        expect(
          mutedSurface,
          `theme ${themeKey} muted/surface contrast = ${mutedSurface} (textMuted=${textMuted}, surface=${surface})`
        ).toBeGreaterThanOrEqual(4.5)
        expect(linkSurface, `theme ${themeKey} link/surface contrast = ${linkSurface}`).toBeGreaterThanOrEqual(4.5)

        const actionPairs = [
          ['primary', primary, onPrimary],
          ['primary-hover', primaryHover, onPrimary],
          ['primary-active', primaryActive, onPrimary],
          ['success', success, onSuccess],
          ['warning', warning, onWarning],
          ['error', error, onError],
          ['info', info, onInfo]
        ]

        actionPairs.forEach(([name, background, foreground]) => {
          const ratio = contrastRatio(foreground, background)
          expect(
            ratio,
            `theme ${themeKey} ${name}/on-${name} contrast = ${ratio} (${foreground} on ${background})`
          ).toBeGreaterThanOrEqual(4.5)
        })

        const feedbackPairs = [
          ['success', success, onSuccess],
          ['warning', warning, onWarning],
          ['error', error, onError],
          ['info', info, onInfo]
        ]

        feedbackPairs.forEach(([name, background, foreground]) => {
          const hover = mixSrgb(background, text, 0.88)
          const active = mixSrgb(background, text, 0.75)

          expect(
            contrastRatio(foreground, hover),
            `theme ${themeKey} ${name}-hover/on-${name} contrast`
          ).toBeGreaterThanOrEqual(4.5)
          expect(
            contrastRatio(foreground, active),
            `theme ${themeKey} ${name}-active/on-${name} contrast`
          ).toBeGreaterThanOrEqual(4.5)
        })

        const focusSurface = contrastRatio(focus, surface)
        expect(
          focusSurface,
          `theme ${themeKey} focus/surface contrast = ${focusSurface}`
        ).toBeGreaterThanOrEqual(3)
      }),
      { numRuns: 100 }
    )
  })
})
