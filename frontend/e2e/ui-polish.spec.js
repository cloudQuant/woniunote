import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

/**
 * E2E coverage for the "迭代 12 — UI 打磨与优化" spec (ui-polish-refinement).
 *
 * These assertions need a real browser layout engine + media-query evaluation,
 * so they live in Playwright rather than the jsdom unit suite:
 *   - R5.1 移动端可达搜索入口（在文章列表上方可见可点击）
 *   - R6   登录弹窗宽度自适应（<520px 不溢出；≥520px 约 520px）
 *   - R7   首页最大阅读宽度与边距（宽屏居中不贴边；窄屏单列留边）
 *   - R9 / R14.4 减弱动效（slogan animation:none、卡片 hover 无 transform）
 *   - R14  悬停 box-shadow 变化
 *
 * Backend is mocked via support/mockApi.js (same as the other specs); the
 * mocked list renders '量化投资入门' inside '.article-item' cards.
 */

/** Read a computed style property from the first element matching `sel`. */
function readStyle(page, sel, prop) {
  return page.evaluate(
    ({ sel, prop }) => {
      const el = document.querySelector(sel)
      return el ? window.getComputedStyle(el)[prop] : null
    },
    { sel, prop }
  )
}

test.describe('UI polish — responsive layout, dialog, reduced motion, hover', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  // ── R5.1 移动端搜索入口 ──────────────────────────────────────────────
  test('mobile: search entry is visible above the article list and navigates on submit', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 })
    await page.goto('/')

    const searchBar = page.locator('.search-bar')
    await expect(searchBar).toBeVisible()

    // The article list must have rendered so we can compare vertical position.
    const firstArticle = page.locator('.article-item').first()
    await expect(firstArticle).toBeVisible()

    // Search entry sits above the list (no need to scroll past the articles).
    const searchBox = await searchBar.boundingBox()
    const articleBox = await firstArticle.boundingBox()
    expect(searchBox).not.toBeNull()
    expect(articleBox).not.toBeNull()
    expect(searchBox.y).toBeLessThan(articleBox.y)

    // Typing a keyword and submitting navigates to the search route (R5.2).
    await searchBar.locator('input').first().fill('python')
    await searchBar.getByRole('button', { name: '搜索' }).click()
    await expect(page).toHaveURL(/\/search\?keyword=python/)
  })

  // ── R6 登录弹窗宽度自适应 ────────────────────────────────────────────
  test('dialog: width does not overflow a narrow (<520px) viewport', async ({ page }) => {
    const viewportWidth = 375
    await page.setViewportSize({ width: viewportWidth, height: 800 })
    await page.goto('/')

    await page.locator('.login-link').click()
    const dialog = page.locator('.login-dialog')
    await expect(dialog).toBeVisible()

    // width = min(520px, 92vw) → at 375px viewport that's ~345px (92vw).
    await expect
      .poll(async () => {
        const box = await dialog.boundingBox()
        return box ? Math.round(box.width) : null
      })
      .toBeLessThanOrEqual(viewportWidth)

    const box = await dialog.boundingBox()
    // No horizontal overflow, and roughly 92vw (≈345px) — allow generous slack.
    expect(box.width).toBeLessThanOrEqual(viewportWidth)
    expect(box.width).toBeGreaterThanOrEqual(300)
    expect(box.x).toBeGreaterThanOrEqual(-1)
    expect(box.x + box.width).toBeLessThanOrEqual(viewportWidth + 1)
  })

  test('dialog: width is approximately 520px on a wide (≥520px) viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/')

    await page.locator('.login-link').click()
    const dialog = page.locator('.login-dialog')
    await expect(dialog).toBeVisible()

    // width = min(520px, 92vw) → at 1280px viewport that's the 520px cap.
    await expect
      .poll(async () => {
        const box = await dialog.boundingBox()
        return box ? Math.round(box.width) : null
      })
      .toBeGreaterThanOrEqual(500)

    const box = await dialog.boundingBox()
    expect(box.width).toBeGreaterThanOrEqual(500)
    expect(box.width).toBeLessThanOrEqual(540)
  })

  // ── R7 首页最大阅读宽度与边距 ────────────────────────────────────────
  test('home: content is capped and horizontally centered on a wide viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 })
    await page.goto('/')

    const container = page.locator('.home-container')
    await expect(container).toBeVisible()
    // Ensure the list has painted so layout is stable.
    await expect(page.locator('.article-item').first()).toBeVisible()

    const box = await container.boundingBox()
    expect(box).not.toBeNull()

    // Constrained to the max reading width (≤1200px, allow a few px tolerance).
    expect(box.width).toBeLessThanOrEqual(1205)

    // Centered: left margin ≈ right margin (computed against the client width,
    // which excludes any vertical scrollbar).
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
    const left = box.x
    const right = clientWidth - box.x - box.width
    // Content is not flush to the edge on a wide screen.
    expect(left).toBeGreaterThan(50)
    expect(Math.abs(left - right)).toBeLessThanOrEqual(12)
  })

  test('home: keeps side padding (content not flush to edge) on a narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 })
    await page.goto('/')

    const container = page.locator('.home-container')
    await expect(container).toBeVisible()

    // Mobile breakpoint padding is var(--wn-space-4) = 16px on both sides.
    const paddingLeft = await readStyle(page, '.home-container', 'paddingLeft')
    const paddingRight = await readStyle(page, '.home-container', 'paddingRight')
    expect(paddingLeft).toBe('16px')
    expect(paddingRight).toBe('16px')

    // The container itself starts at the viewport edge, but its inner content
    // is inset by the padding — confirm the box width leaves room for padding.
    const box = await container.boundingBox()
    expect(box.width).toBeLessThanOrEqual(375)
  })

  // ── R9 / R14.4 减弱动效 ──────────────────────────────────────────────
  test('reduced motion: slogan animation is none and card hover has no transform', async ({ page, isMobile }) => {
    // Slogan is hidden and hover semantics differ on touch devices; this
    // assertion targets the desktop layout/interaction model.
    test.skip(isMobile, 'desktop hover/slogan behavior only')
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/')

    // Slogan only renders at desktop widths (hidden <=768px), so use 1280px.
    const slogan = page.locator('.slogan')
    await expect(slogan).toBeVisible()

    // R9.1: marquee animation is disabled under reduced motion.
    const animationName = await readStyle(page, '.slogan', 'animationName')
    expect(animationName).toBe('none')

    // R14.4: card hover must not apply a translate/transform under reduced motion.
    const firstArticle = page.locator('.article-item').first()
    await expect(firstArticle).toBeVisible()
    await firstArticle.hover()
    await expect
      .poll(async () => readStyle(page, '.article-item', 'transform'))
      .toBe('none')
  })

  // ── R14 悬停 box-shadow 变化 ─────────────────────────────────────────
  test('normal motion: hovering a card changes its box-shadow (elevation)', async ({ page, isMobile }) => {
    test.skip(isMobile, 'hover elevation is a pointer-device interaction')
    await page.emulateMedia({ reducedMotion: 'no-preference' })
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/')

    const firstArticle = page.locator('.article-item').first()
    await expect(firstArticle).toBeVisible()

    const before = await readStyle(page, '.article-item', 'boxShadow')
    expect(before).toBeTruthy()
    expect(before).not.toBe('none')

    await firstArticle.hover()

    // The transition settles to var(--wn-elevation-hover); poll until it differs.
    await expect
      .poll(async () => readStyle(page, '.article-item', 'boxShadow'))
      .not.toBe(before)

    const after = await readStyle(page, '.article-item', 'boxShadow')
    expect(after).toBeTruthy()
    expect(after).not.toBe('none')
    expect(after).not.toBe(before)
  })
})
