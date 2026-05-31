import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import fc from 'fast-check'

import { parseThemeTokens } from '@/utils/contrast'

/**
 * tokens.spec.js —— 设计令牌默认值完备性（防 FOUC）属性测试。
 *
 * 解析 tokens.css 的 :root 块后，断言约定的 spacing / font-size / line-height
 * 令牌均存在且具有非空默认值，保证 JS 未执行时仍有合理回退（R13.3）。
 */

// 读取 tokens.css 源文本。vitest 以 frontend/ 为 cwd，按工程相对路径解析，
// 避免 jsdom 下 import.meta.url 非 file scheme 与 `?raw` 在 css:false 时返回空串的问题。
const tokensCssPath = path.resolve(process.cwd(), 'src/assets/themes/tokens.css')
const tokensCss = readFileSync(tokensCssPath, 'utf-8')

// 仅取 :root 块内的令牌默认值（主题覆盖位于 [data-theme] 选择器，与默认值无关）。
function extractRootBlock(cssText) {
  const start = cssText.indexOf(':root')
  if (start === -1) return ''
  const braceStart = cssText.indexOf('{', start)
  if (braceStart === -1) return ''
  let depth = 0
  for (let i = braceStart; i < cssText.length; i += 1) {
    const ch = cssText[i]
    if (ch === '{') depth += 1
    else if (ch === '}') {
      depth -= 1
      if (depth === 0) return cssText.slice(braceStart + 1, i)
    }
  }
  return ''
}

const rootTokens = parseThemeTokens(extractRootBlock(tokensCss))

// 约定令牌名集合（与设计「Design Token Additions」一致）。
const SPACING_TOKENS = [
  '--wn-space-1',
  '--wn-space-2',
  '--wn-space-3',
  '--wn-space-4',
  '--wn-space-5',
  '--wn-space-6',
  '--wn-space-7',
  '--wn-space-8'
]
const FONT_SIZE_TOKENS = [
  '--wn-font-size-xs',
  '--wn-font-size-sm',
  '--wn-font-size-base',
  '--wn-font-size-md',
  '--wn-font-size-lg',
  '--wn-font-size-xl',
  '--wn-font-size-2xl'
]
const LINE_HEIGHT_TOKENS = [
  '--wn-line-height-tight',
  '--wn-line-height-snug',
  '--wn-line-height-normal',
  '--wn-line-height-relaxed'
]
const CONVENTION_TOKENS = [
  ...SPACING_TOKENS,
  ...FONT_SIZE_TOKENS,
  ...LINE_HEIGHT_TOKENS
]

describe('tokens.css 设计令牌默认值完备性', () => {
  // Feature: ui-polish-refinement, Property 4: For any 约定令牌名 n ∈ {--wn-space-1..--wn-space-8, --wn-font-size-xs..--wn-font-size-2xl, --wn-line-height-tight..--wn-line-height-relaxed}, 解析 tokens.css 的 :root 块后，n 均存在且具有非空默认值。
  it('每个约定的 spacing/font-size/line-height 令牌在 :root 存在且默认值非空', () => {
    fc.assert(
      fc.property(fc.constantFrom(...CONVENTION_TOKENS), (tokenName) => {
        expect(rootTokens).toHaveProperty(tokenName)
        const value = rootTokens[tokenName]
        expect(typeof value).toBe('string')
        expect(value.trim().length).toBeGreaterThan(0)
      }),
      { numRuns: 100 }
    )
  })
})
