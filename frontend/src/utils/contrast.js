/**
 * @module utils/contrast
 * @description WCAG 对比度计算与 CSS 设计令牌解析的无依赖纯函数。
 *
 * 服务于：
 *  - R10 九套主题正文/次级文本对比度校验（relativeLuminance / contrastRatio）
 *  - R13 设计令牌默认值完备性校验（parseThemeTokens）
 *
 * 全部为纯函数：无副作用、无第三方依赖，便于单元/属性测试覆盖（含 functions 阈值）与复用。
 */

/**
 * 将十六进制颜色解析为 [r, g, b]（每通道 0-255）。
 *
 * 支持以下形式（可带或不带前导 `#`）：
 *  - 3 位简写："#abc" / "abc"（展开为 "aabbcc"）
 *  - 6 位完整："#aabbcc" / "aabbcc"
 *
 * @param {string} hex - 十六进制颜色字符串
 * @returns {[number, number, number]|null} RGB 三元组；无法解析时返回 null
 */
export function hexToRgb(hex) {
  if (typeof hex !== 'string') return null
  let h = hex.trim().replace(/^#/, '')
  // 3 位简写展开为 6 位（#abc -> aabbcc）
  if (/^[0-9a-fA-F]{3}$/.test(h)) {
    h = h.split('').map((c) => c + c).join('')
  }
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null
  const num = parseInt(h, 16)
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255]
}

/**
 * 线性化单个 sRGB 通道（WCAG 相对亮度公式的逐通道部分）。
 *
 * @param {number} channel - 0-255 的通道值
 * @returns {number} 线性化后的 0..1 值
 */
function linearizeChannel(channel) {
  const c = channel / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/**
 * 计算颜色的 WCAG 相对亮度（relative luminance）。
 *
 * L = 0.2126·R + 0.7152·G + 0.0722·B，其中 R/G/B 为线性化后的通道值。
 *
 * @param {string} hex - 十六进制颜色字符串
 * @returns {number} 相对亮度，范围 0..1；无法解析时返回 NaN
 */
export function relativeLuminance(hex) {
  const rgb = hexToRgb(hex)
  if (!rgb) return NaN
  const [r, g, b] = rgb
  return (
    0.2126 * linearizeChannel(r) +
    0.7152 * linearizeChannel(g) +
    0.0722 * linearizeChannel(b)
  )
}

/**
 * 计算两色之间的 WCAG 对比度（contrast ratio），范围 1..21。
 *
 * ratio = (L_lighter + 0.05) / (L_darker + 0.05)。结果与前景/背景的传入顺序无关。
 *
 * @param {string} fg - 前景色（十六进制）
 * @param {string} bg - 背景色（十六进制）
 * @returns {number} 对比度，范围 1..21；任一颜色无法解析时返回 NaN
 */
export function contrastRatio(fg, bg) {
  const l1 = relativeLuminance(fg)
  const l2 = relativeLuminance(bg)
  if (Number.isNaN(l1) || Number.isNaN(l2)) return NaN
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * 从 CSS 文本中提取所有 `--wn-*` 设计令牌的声明值。
 *
 * 例："--wn-color-text: #141413;" → { '--wn-color-text': '#141413' }。
 * 同名令牌以最后一次声明为准（贴合 CSS 同特异度级联）。值会去除首尾空白。
 * 仅提取 `--wn-` 前缀的令牌，忽略 `--el-*` 等其他自定义属性与普通声明。
 *
 * @param {string} cssText - CSS 源文本
 * @returns {Record<string, string>} 令牌名到值的映射
 */
export function parseThemeTokens(cssText) {
  const tokens = {}
  if (typeof cssText !== 'string') return tokens
  const re = /(--wn-[\w-]+)\s*:\s*([^;]+);/g
  let match
  while ((match = re.exec(cssText)) !== null) {
    tokens[match[1]] = match[2].trim()
  }
  return tokens
}

export default {
  hexToRgb,
  relativeLuminance,
  contrastRatio,
  parseThemeTokens
}
