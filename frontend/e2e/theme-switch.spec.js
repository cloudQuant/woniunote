import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

test.describe('Theme switching', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('defaults to the claude theme on first visit', async ({ page }) => {
    await page.goto('/')
    const theme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    expect(theme).toBe('claude')
  })

  test('each theme updates html attributes, selected state, and persistence', async ({ page }) => {
    await page.goto('/')
    const trigger = page.locator('button.theme-switcher-trigger')
    const themeCases = [
      ['claude', false],
      ['notion', false],
      ['vercel', false],
      ['stripe', false],
      ['starbucks', false],
      ['linear', true],
      ['spotify', true],
      ['supabase', true],
      ['sentry', true],
    ]

    for (const [themeKey, isDarkTheme] of themeCases) {
      await trigger.click()
      const themeCell = page.locator(`[data-theme-key="${themeKey}"]`)
      await expect(themeCell).toBeVisible()
      await themeCell.click()

      await expect.poll(async () =>
        page.evaluate(() => document.documentElement.getAttribute('data-theme'))
      ).toBe(themeKey)
      await expect(themeCell).toHaveAttribute('aria-pressed', 'true')

      const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
      expect(isDark).toBe(isDarkTheme)

      const persisted = await page.evaluate(() => localStorage.getItem('wn-theme'))
      expect(persisted).toBe(themeKey)
    }

    // Reload preserves the final choice (no FOUC fallback to the default theme).
    await page.reload()
    await expect.poll(async () =>
      page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    ).toBe('sentry')
  })

  test('the theme selector can be opened and applied with the keyboard', async ({ page }) => {
    await page.goto('/')
    const trigger = page.locator('button.theme-switcher-trigger')

    await trigger.focus()
    await expect(trigger).toBeFocused()
    await page.keyboard.press('Enter')

    const linear = page.locator('[data-theme-key="linear"]')
    await expect(linear).toBeVisible()
    await linear.focus()
    await page.keyboard.press('Enter')

    await expect.poll(async () =>
      page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    ).toBe('linear')
  })

  test('the grouped selector stays inside a narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await page.locator('button.theme-switcher-trigger').click()

    const panel = page.locator('.theme-switcher-popover')
    await expect(panel).toBeVisible()
    const box = await panel.boundingBox()

    expect(box).not.toBeNull()
    expect(box.x).toBeGreaterThanOrEqual(0)
    expect(box.x + box.width).toBeLessThanOrEqual(390)
  })
})
