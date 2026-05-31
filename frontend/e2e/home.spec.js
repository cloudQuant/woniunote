import { test, expect } from '@playwright/test'
import { mockApi } from './support/mockApi'

test.describe('Home & navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
  })

  test('loads the home page with header, article list and footer', async ({ page }) => {
    await page.goto('/')
    // Brand title is set from route meta.
    await expect(page).toHaveTitle(/cloudQuant/)
    // Header logo + footer copyright present.
    await expect(page.locator('.app-header')).toBeVisible()
    await expect(page.locator('.app-footer')).toContainText('版权所有')
    // Articles from the mocked list render.
    await expect(page.getByText('量化投资入门').first()).toBeVisible()
  })

  test('navigates to an article detail from the list', async ({ page }) => {
    await page.goto('/')
    await page.getByText('量化投资入门').first().click()
    await expect(page).toHaveURL(/\/article\/1/)
    await expect(page.locator('.article-body, .article-content, article').first()).toBeVisible()
  })

  test('navigates to a category via the nav dropdown route', async ({ page }) => {
    await page.goto('/type/101/1')
    await expect(page).toHaveURL(/\/type\/101/)
  })

  test('shows the 404 page for unknown routes', async ({ page }) => {
    await page.goto('/this/does/not/exist')
    await expect(page.getByText('404')).toBeVisible()
    await expect(page.getByText('页面未找到')).toBeVisible()
  })

  test('search navigation works from the URL', async ({ page }) => {
    await page.goto('/search?keyword=python')
    await expect(page).toHaveURL(/\/search/)
  })
})
