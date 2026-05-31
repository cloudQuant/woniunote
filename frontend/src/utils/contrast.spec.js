import { describe, it, expect } from 'vitest'
import {
  hexToRgb,
  relativeLuminance,
  contrastRatio,
  parseThemeTokens
} from './contrast'
import contrastDefault from './contrast'

describe('utils/contrast - hexToRgb', () => {
  it('parses 6-digit hex with and without leading #', () => {
    expect(hexToRgb('#ffffff')).toEqual([255, 255, 255])
    expect(hexToRgb('000000')).toEqual([0, 0, 0])
    expect(hexToRgb('#cc785c')).toEqual([204, 120, 92])
  })

  it('expands 3-digit shorthand', () => {
    expect(hexToRgb('#abc')).toEqual([0xaa, 0xbb, 0xcc])
    expect(hexToRgb('fff')).toEqual([255, 255, 255])
  })

  it('trims surrounding whitespace', () => {
    expect(hexToRgb('  #141413  ')).toEqual([20, 20, 19])
  })

  it('returns null for invalid input', () => {
    expect(hexToRgb('not-a-color')).toBeNull()
    expect(hexToRgb('#12345')).toBeNull()
    expect(hexToRgb('#1234567')).toBeNull()
    expect(hexToRgb(123)).toBeNull()
    expect(hexToRgb(null)).toBeNull()
  })
})

describe('utils/contrast - relativeLuminance', () => {
  it('returns 0 for black and 1 for white', () => {
    expect(relativeLuminance('#000000')).toBeCloseTo(0, 6)
    expect(relativeLuminance('#ffffff')).toBeCloseTo(1, 6)
  })

  it('returns a value in [0, 1] for arbitrary colors', () => {
    const lum = relativeLuminance('#cc785c')
    expect(lum).toBeGreaterThan(0)
    expect(lum).toBeLessThan(1)
  })

  it('returns NaN for unparseable input', () => {
    expect(Number.isNaN(relativeLuminance('zzz'))).toBe(true)
  })
})

describe('utils/contrast - contrastRatio', () => {
  it('is 21 for black on white (maximum)', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 5)
  })

  it('is 1 for identical colors (minimum)', () => {
    expect(contrastRatio('#777777', '#777777')).toBeCloseTo(1, 5)
  })

  it('is order-independent (fg/bg swap yields same ratio)', () => {
    const a = contrastRatio('#141413', '#fffdfa')
    const b = contrastRatio('#fffdfa', '#141413')
    expect(a).toBeCloseTo(b, 10)
  })

  it('stays within the 1..21 range', () => {
    const ratio = contrastRatio('#6c6a64', '#fffdfa')
    expect(ratio).toBeGreaterThanOrEqual(1)
    expect(ratio).toBeLessThanOrEqual(21)
  })

  it('returns NaN when either color is invalid', () => {
    // 'zzz' is non-hex (unlike 'bad', whose chars are all valid hex digits).
    expect(Number.isNaN(contrastRatio('zzz', '#ffffff'))).toBe(true)
    expect(Number.isNaN(contrastRatio('#ffffff', 'zzz'))).toBe(true)
  })
})

describe('utils/contrast - parseThemeTokens', () => {
  it('extracts --wn-* tokens with trimmed values', () => {
    const css = `:root {
      --wn-color-text: #141413;
      --wn-space-4:  16px ;
      --el-color-primary: var(--wn-color-primary);
      color: red;
    }`
    const tokens = parseThemeTokens(css)
    expect(tokens['--wn-color-text']).toBe('#141413')
    expect(tokens['--wn-space-4']).toBe('16px')
  })

  it('ignores non --wn-* custom properties and plain declarations', () => {
    const css = ':root { --el-bg-color: #fff; --wn-color-primary: #cc785c; margin: 0; }'
    const tokens = parseThemeTokens(css)
    expect(tokens['--el-bg-color']).toBeUndefined()
    expect(tokens['--wn-color-primary']).toBe('#cc785c')
    expect(Object.keys(tokens)).toEqual(['--wn-color-primary'])
  })

  it('keeps the last declaration when a token repeats', () => {
    const css = '--wn-color-text: #000; --wn-color-text: #111;'
    expect(parseThemeTokens(css)['--wn-color-text']).toBe('#111')
  })

  it('preserves complex values like color-mix and rgba', () => {
    const css =
      '--wn-color-nav-hover: rgba(255, 255, 255, 0.12); ' +
      '--wn-focus-ring: 0 0 0 3px color-mix(in srgb, var(--wn-color-primary) 45%, transparent);'
    const tokens = parseThemeTokens(css)
    expect(tokens['--wn-color-nav-hover']).toBe('rgba(255, 255, 255, 0.12)')
    expect(tokens['--wn-focus-ring']).toBe(
      '0 0 0 3px color-mix(in srgb, var(--wn-color-primary) 45%, transparent)'
    )
  })

  it('returns an empty object for empty or non-string input', () => {
    expect(parseThemeTokens('')).toEqual({})
    expect(parseThemeTokens(null)).toEqual({})
    expect(parseThemeTokens(undefined)).toEqual({})
  })
})

describe('utils/contrast - default export', () => {
  it('exposes all named functions', () => {
    expect(contrastDefault.hexToRgb).toBe(hexToRgb)
    expect(contrastDefault.relativeLuminance).toBe(relativeLuminance)
    expect(contrastDefault.contrastRatio).toBe(contrastRatio)
    expect(contrastDefault.parseThemeTokens).toBe(parseThemeTokens)
  })
})
