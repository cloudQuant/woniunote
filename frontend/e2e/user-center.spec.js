import { test, expect } from '@playwright/test'
import { mockApi, loginAs } from './support/mockApi'

test.describe('User center', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await loginAs(page, 'user')
  })

  test('profile sub-route renders the user info', async ({ page }) => {
    await page.goto('/user')
    await expect(page.locator('.user-center-page')).toBeVisible()
    // The nickname appears in the sidebar user card.
    await expect(page.locator('.user-name')).toContainText('tester')
  })

  test('my articles sub-route lists the user articles', async ({ page }) => {
    await page.goto('/user/articles')
    await expect(page).toHaveURL(/\/user\/articles/)
    await expect(page.locator('.user-content').getByText('量化投资入门').first()).toBeVisible()
  })

  test('my favorites sub-route renders (empty state ok)', async ({ page }) => {
    await page.goto('/user/favorites')
    await expect(page).toHaveURL(/\/user\/favorites/)
    // Scope to the content heading (the sidebar also has a "我的收藏" menu item).
    await expect(page.locator('.user-content .page-title')).toContainText('我的收藏')
  })

  test('my credits sub-route shows the balance summary', async ({ page }) => {
    await page.goto('/user/credits')
    await expect(page).toHaveURL(/\/user\/credits/)
    await expect(page.locator('.user-content .page-title').first()).toContainText('我的积分')
  })
})
