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

  test('switching to a dark theme updates html attributes and persists', async ({ page }) => {
    await page.goto('/')
    // Open the theme switcher in the header.
    const trigger = page.getByText('主题', { exact: false }).first()
    await trigger.click()

    // Pick the Linear (dark) theme from the popover.
    const linear = page.getByText('Linear', { exact: false }).first()
    await linear.click()

    await expect.poll(async () =>
      page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    ).toBe('linear')

    const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(isDark).toBe(true)

    const persisted = await page.evaluate(() => localStorage.getItem('wn-theme'))
    expect(persisted).toBe('linear')

    // Reload preserves the chosen theme (no FOUC fallback to default).
    await page.reload()
    await expect.poll(async () =>
      page.evaluate(() => document.documentElement.getAttribute('data-theme'))
    ).toBe('linear')
  })
})
